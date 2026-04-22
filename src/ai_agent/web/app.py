from __future__ import annotations

import json
import mimetypes
import os
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..agent import AIAgent
from ..chat import ChatOrchestrator
from ..config import AgentConfig, PROVIDER_ALIASES, SUPPORTED_LLM_PROVIDERS
from ..models import ChatMessage, Conversation, Skill
from .system_ops import pick_folder_via_native_dialog, query_ollama_versions, start_ollama_service


THEMES = {"amber", "ocean", "graphite"}
ALLOWED_UPLOAD_EXTS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".tsv",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".sql",
    ".xml",
    ".html",
    ".css",
}
MAX_UPLOAD_FILE_BYTES = 2 * 1024 * 1024
MAX_UPLOAD_TEXT_CHARS = 12000
MAX_UPLOAD_FILES_PER_MESSAGE = 5
MODEL_FOLDER_DETECTION_CACHE_KEY = "model_folder_detection_cache"


class CreateConversationPayload(BaseModel):
    title: str | None = None


class RenameConversationPayload(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class SendMessagePayload(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    model: str | None = None
    upload_ids: list[str] = Field(default_factory=list, max_length=MAX_UPLOAD_FILES_PER_MESSAGE)


class SelectModelPayload(BaseModel):
    model: str = Field(min_length=1, max_length=160)


class PullModelPayload(BaseModel):
    model: str = Field(min_length=1, max_length=160)
    select_after_pull: bool | None = None


class SkillPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=240)
    instruction: str = Field(min_length=1, max_length=8000)
    trigger_keywords: str = Field(default="", max_length=400)
    enabled: bool = True


class SkillTogglePayload(BaseModel):
    enabled: bool


class SettingsUpdatePayload(BaseModel):
    theme: str | None = Field(default=None, max_length=40)
    llm_provider: str | None = Field(default=None, max_length=40)
    llm_model: str | None = Field(default=None, max_length=160)
    ollama_models_dir: str | None = Field(default=None, max_length=600)
    ollama_base_url: str | None = Field(default=None, max_length=200)
    openai_base_url: str | None = Field(default=None, max_length=300)
    openai_api_key: str | None = Field(default=None, max_length=300)
    openai_model: str | None = Field(default=None, max_length=160)
    llm_history_limit: int | None = Field(default=None, ge=4, le=80)
    intent_confidence_threshold: float | None = Field(default=None, ge=0.05, le=0.98)
    auto_select_after_pull: bool | None = None
    enter_to_send: bool | None = None
    web_port_preferred: int | None = Field(default=None, ge=1000, le=65535)


def _conversation_to_dict(item: Conversation) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "last_message_preview": item.last_message_preview,
        "message_count": item.message_count,
    }


def _message_to_dict(item: ChatMessage) -> dict[str, Any]:
    return {
        "id": item.id,
        "conversation_id": item.conversation_id,
        "role": item.role,
        "content": item.content,
        "created_at": item.created_at,
    }


def _skill_to_dict(item: Skill) -> dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "instruction": item.instruction,
        "trigger_keywords": item.trigger_keywords,
        "enabled": item.enabled,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _default_db_path() -> Path:
    env_path = os.getenv("AURORA_DB_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (Path.cwd() / "data" / "agent.db").resolve()


def _ndjson(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


def _split_keywords(raw: str) -> list[str]:
    chunks = re.split(r"[,，\n]", raw)
    return [item.strip() for item in chunks if item.strip()]


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"1", "true", "yes", "on", "y"}


def _safe_path(raw: str) -> str:
    return str(Path(raw).expanduser().resolve())


def _mask_secret(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        return ""
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}***{cleaned[-4:]}"


def _normalize_upload_filename(raw: str | None) -> str:
    if not raw:
        return "upload.txt"
    cleaned = Path(raw).name.strip()
    if not cleaned:
        return "upload.txt"
    return cleaned[:180]


def _decode_upload_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "gb18030"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def _extract_upload_text(filename: str, raw_bytes: bytes) -> tuple[str, bool]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(status_code=400, detail=f"暂不支持该文件类型：{suffix or 'unknown'}")

    text = _decode_upload_text(raw_bytes).replace("\x00", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="文件内容为空或无法解析为文本。")

    truncated = len(text) > MAX_UPLOAD_TEXT_CHARS
    if truncated:
        text = text[:MAX_UPLOAD_TEXT_CHARS]
    return text, truncated


def _resolve_upload_records(upload_ids: list[str], upload_store: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    missing: list[str] = []
    for upload_id in upload_ids[:MAX_UPLOAD_FILES_PER_MESSAGE]:
        normalized = upload_id.strip()
        if not normalized:
            continue
        item = upload_store.get(normalized)
        if item is None:
            missing.append(normalized)
            continue
        resolved.append(item)
    if missing:
        raise HTTPException(status_code=400, detail=f"部分附件已失效，请重新上传：{', '.join(missing[:3])}")
    return resolved


def _build_upload_prompt_context(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    blocks: list[str] = [
        "以下是用户上传的文件内容。请优先依据这些文件回答，并明确标注你使用了哪些文件信息。",
    ]
    for index, item in enumerate(items, start=1):
        blocks.append(
            "\n".join(
                [
                    f"### 文件 {index}",
                    f"文件名：{item['name']}",
                    f"文件大小：{item['size']} 字节",
                    "内容：",
                    item["content"],
                ]
            )
        )
    return "\n\n".join(blocks)


def _cleanup_upload_records(upload_ids: list[str], upload_store: dict[str, dict[str, Any]]) -> None:
    for upload_id in upload_ids:
        item = upload_store.pop(upload_id, None)
        if not item:
            continue
        try:
            saved_path = item.get("saved_path")
            if saved_path:
                Path(str(saved_path)).unlink(missing_ok=True)
        except OSError:
            continue


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex((host, port)) != 0


def _find_available_port(host: str, preferred_port: int, span: int = 40) -> int:
    port = max(1, preferred_port)
    if _is_port_available(host, port):
        return port
    for offset in range(1, span + 1):
        candidate = port + offset
        if candidate > 65535:
            break
        if _is_port_available(host, candidate):
            return candidate
    return preferred_port


def _gather_model_refs(manifests_dir: Path, limit: int = 16) -> list[str]:
    refs: list[str] = []
    if not manifests_dir.exists() or not manifests_dir.is_dir():
        return refs
    for item in manifests_dir.rglob("*"):
        if not item.is_file():
            continue
        refs.append(item.relative_to(manifests_dir).as_posix())
        if len(refs) >= limit:
            break
    return refs


def _active_model_dir_info(agent: AIAgent) -> tuple[str, str]:
    configured = (agent.memory.get_setting("ollama_models_dir") or "").strip()
    env_dir = os.getenv("OLLAMA_MODELS", "").strip()
    if configured:
        return configured, "setting"
    if env_dir:
        return env_dir, "env"
    return str(Path.home() / ".ollama" / "models"), "default"


def _empty_detection_snapshot(agent: AIAgent) -> dict[str, Any]:
    active_path, active_source = _active_model_dir_info(agent)
    return {
        "active_path": active_path,
        "active_source": active_source,
        "items": [],
        "detected_at": None,
        "note": (
            "点击“重新检测”后才会扫描本机模型目录。"
            "你在设置里指定的目录会作为模型下载目标（通常需要重启 Ollama 服务后完全生效）。"
        ),
    }


def _detect_model_folders(agent: AIAgent) -> dict[str, Any]:
    configured = (agent.memory.get_setting("ollama_models_dir") or "").strip()
    env_dir = os.getenv("OLLAMA_MODELS", "").strip()

    candidates_raw: list[str] = []
    if configured:
        candidates_raw.append(configured)
    if env_dir and env_dir != configured:
        candidates_raw.append(env_dir)

    home_default = Path.home() / ".ollama" / "models"
    localappdata = os.getenv("LOCALAPPDATA")
    programdata = os.getenv("PROGRAMDATA")
    candidates_raw.append(str(home_default))
    if localappdata:
        candidates_raw.append(str(Path(localappdata) / "Ollama" / "models"))
    if programdata:
        candidates_raw.append(str(Path(programdata) / "Ollama" / "models"))

    unique_paths: list[str] = []
    seen: set[str] = set()
    for raw in candidates_raw:
        cleaned = raw.strip()
        if not cleaned:
            continue
        try:
            normalized = _safe_path(cleaned)
        except Exception:
            normalized = cleaned
        marker = normalized.lower()
        if marker in seen:
            continue
        unique_paths.append(normalized)
        seen.add(marker)

    items: list[dict[str, Any]] = []
    for raw_path in unique_paths:
        path = Path(raw_path)
        exists = path.exists() and path.is_dir()
        manifests = path / "manifests"
        refs = _gather_model_refs(manifests)
        writable_target = path if exists else path.parent
        writable = writable_target.exists() and os.access(writable_target, os.W_OK)
        items.append(
            {
                "path": str(path),
                "exists": exists,
                "writable": writable,
                "manifest_count": len(refs),
                "sample_models": refs,
            }
        )

    active_path, active_source = _active_model_dir_info(agent)

    return {
        "active_path": active_path,
        "active_source": active_source,
        "items": items,
        "detected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "模型目录变更后，通常需要重启 Ollama 服务才能让下载位置完全生效。",
    }


def _read_detection_snapshot(agent: AIAgent) -> dict[str, Any]:
    cached = (agent.memory.get_setting(MODEL_FOLDER_DETECTION_CACHE_KEY) or "").strip()
    if not cached:
        return _empty_detection_snapshot(agent)

    try:
        parsed = json.loads(cached)
    except json.JSONDecodeError:
        return _empty_detection_snapshot(agent)

    if not isinstance(parsed, dict):
        return _empty_detection_snapshot(agent)

    fallback = _empty_detection_snapshot(agent)
    active_path, active_source = _active_model_dir_info(agent)
    return {
        "active_path": active_path,
        "active_source": active_source,
        "items": parsed.get("items") if isinstance(parsed.get("items"), list) else fallback["items"],
        "detected_at": parsed.get("detected_at"),
        "note": str(parsed.get("note") or fallback["note"]),
    }


def _persist_detection_snapshot(agent: AIAgent, snapshot: dict[str, Any]) -> None:
    agent.memory.set_setting(
        MODEL_FOLDER_DETECTION_CACHE_KEY,
        json.dumps(snapshot, ensure_ascii=False),
    )


def _settings_snapshot(agent: AIAgent) -> dict[str, Any]:
    theme = (agent.memory.get_setting("ui_theme") or "amber").strip().lower()
    if theme not in THEMES:
        theme = "amber"

    provider = (agent.memory.get_setting("llm_provider") or agent.config.llm_provider).strip().lower() or "ollama"
    if provider in {"openai", "dashscope", "bailian", "aliyun", "openai-compatible"}:
        provider = "openai_compatible"
    if provider not in {"ollama", "openai_compatible"}:
        provider = "ollama"
    base_url = (agent.memory.get_setting("ollama_base_url") or agent.config.ollama_base_url).strip()
    openai_base_url = (agent.memory.get_setting("openai_base_url") or agent.config.openai_base_url).strip()
    models_dir = (agent.memory.get_setting("ollama_models_dir") or os.getenv("OLLAMA_MODELS", "")).strip()
    llm_model = agent.config.openai_model if provider == "openai_compatible" else agent.config.ollama_model
    ollama_model = (agent.memory.get_setting("default_model_ollama") or agent.config.ollama_model).strip()
    openai_model = (agent.memory.get_setting("openai_model") or agent.config.openai_model).strip()
    openai_api_key = (agent.memory.get_setting("openai_api_key") or agent.config.openai_api_key).strip()

    raw_history = agent.memory.get_setting("llm_history_limit")
    raw_threshold = agent.memory.get_setting("intent_confidence_threshold")
    raw_port = agent.memory.get_setting("web_port_preferred")

    try:
        history_limit = max(4, min(80, int(raw_history))) if raw_history else agent.config.llm_history_limit
    except ValueError:
        history_limit = agent.config.llm_history_limit

    try:
        intent_threshold = float(raw_threshold) if raw_threshold else agent.config.intent_confidence_threshold
    except ValueError:
        intent_threshold = agent.config.intent_confidence_threshold

    try:
        port_preferred = int(raw_port) if raw_port else int(os.getenv("AURORA_WEB_PORT", "8000"))
    except ValueError:
        port_preferred = 8000

    settings = {
        "theme": theme,
        "llm_provider": provider,
        "llm_model": llm_model,
        "ollama_model": ollama_model,
        "ollama_models_dir": models_dir,
        "ollama_base_url": base_url,
        "openai_base_url": openai_base_url,
        "openai_model": openai_model,
        "openai_has_api_key": bool(openai_api_key),
        "openai_api_key_masked": _mask_secret(openai_api_key),
        "llm_history_limit": max(4, min(80, history_limit)),
        "intent_confidence_threshold": max(0.05, min(0.98, intent_threshold)),
        "auto_select_after_pull": _parse_bool(agent.memory.get_setting("auto_select_after_pull"), True),
        "enter_to_send": _parse_bool(agent.memory.get_setting("enter_to_send"), True),
        "web_port_preferred": max(1000, min(65535, port_preferred)),
    }
    return {
        "settings": settings,
        "model_folder_detection": _read_detection_snapshot(agent),
    }


def create_app(db_path: Path | None = None) -> FastAPI:
    resolved_db_path = db_path.resolve() if db_path else _default_db_path()
    config = AgentConfig.from_db_path(resolved_db_path)
    agent = AIAgent(config)
    orchestrator = ChatOrchestrator(agent)
    static_dir = Path(__file__).resolve().parent / "static"
    upload_dir = resolved_db_path.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Aurora Agent Web", version="0.7.0")
    app.state.orchestrator = orchestrator
    app.state.agent = agent
    app.state.upload_dir = upload_dir
    app.state.upload_store: dict[str, dict[str, Any]] = {}
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def disable_asset_cache(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    @app.get("/api/settings")
    def get_settings() -> dict[str, Any]:
        return _settings_snapshot(agent)

    @app.put("/api/settings")
    def update_settings(payload: SettingsUpdatePayload) -> dict[str, Any]:
        if payload.theme is not None:
            theme = payload.theme.strip().lower()
            if theme not in THEMES:
                raise HTTPException(status_code=400, detail=f"不支持的主题：{payload.theme}")
            agent.memory.set_setting("ui_theme", theme)

        if payload.llm_provider is not None:
            provider = payload.llm_provider.strip().lower()
            if provider and provider not in SUPPORTED_LLM_PROVIDERS and provider not in PROVIDER_ALIASES:
                raise HTTPException(status_code=400, detail=f"不支持的模型提供方：{payload.llm_provider}")

        if payload.auto_select_after_pull is not None:
            agent.memory.set_setting("auto_select_after_pull", "true" if payload.auto_select_after_pull else "false")

        if payload.enter_to_send is not None:
            agent.memory.set_setting("enter_to_send", "true" if payload.enter_to_send else "false")

        if payload.web_port_preferred is not None:
            agent.memory.set_setting("web_port_preferred", str(payload.web_port_preferred))

        if payload.ollama_models_dir is not None and payload.ollama_models_dir.strip():
            try:
                _ = _safe_path(payload.ollama_models_dir.strip())
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"模型目录无效：{exc}") from exc

        try:
            agent.apply_runtime_settings(
                llm_provider=payload.llm_provider,
                ollama_base_url=payload.ollama_base_url,
                openai_base_url=payload.openai_base_url,
                openai_api_key=payload.openai_api_key,
                openai_model=payload.openai_model,
                llm_model=payload.llm_model,
                llm_history_limit=payload.llm_history_limit,
                intent_confidence_threshold=payload.intent_confidence_threshold,
                ollama_models_dir=payload.ollama_models_dir,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return _settings_snapshot(agent)

    @app.post("/api/settings/model-folders/detect")
    def detect_model_folders() -> dict[str, Any]:
        snapshot = _detect_model_folders(agent)
        _persist_detection_snapshot(agent, snapshot)
        return {"model_folder_detection": snapshot}

    @app.post("/api/settings/model-folders/pick")
    def pick_model_folder() -> dict[str, Any]:
        selected = pick_folder_via_native_dialog()
        if not selected:
            return {"picked": False}

        resolved = _safe_path(selected)
        Path(resolved).mkdir(parents=True, exist_ok=True)
        try:
            agent.apply_runtime_settings(ollama_models_dir=resolved)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "picked": True,
            "path": resolved,
            "snapshot": _settings_snapshot(agent),
        }

    @app.post("/api/ollama/start")
    def start_ollama() -> dict[str, Any]:
        base_url = (agent.memory.get_setting("ollama_base_url") or agent.config.ollama_base_url).strip()
        if not base_url:
            base_url = "http://127.0.0.1:11434"
        result = start_ollama_service(base_url)
        result["runtime"] = agent.runtime_metadata
        return result

    @app.get("/api/ollama/version")
    def ollama_version() -> dict[str, Any]:
        base_url = (agent.memory.get_setting("ollama_base_url") or agent.config.ollama_base_url).strip()
        if not base_url:
            base_url = "http://127.0.0.1:11434"
        return query_ollama_versions(base_url)

    @app.get("/api/models")
    def list_models() -> dict[str, Any]:
        runtime_info = agent.runtime_metadata
        return {
            "provider": runtime_info["provider"],
            "current_model": runtime_info["model"],
            "items": runtime_info["available_models"],
            "reachable": runtime_info["reachable"],
            "supports_model_pull": runtime_info.get("supports_model_pull", False),
        }

    @app.get("/api/model-library")
    def list_model_library(q: str = "", page: int = 1) -> dict[str, Any]:
        try:
            items = agent.list_remote_models(query=q, page=page)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        runtime_info = agent.runtime_metadata
        local_models = set(runtime_info["available_models"])
        current_model = runtime_info["model"]
        enriched: list[dict[str, Any]] = []
        for item in items:
            family = item.get("family") or item.get("name") or ""
            has_downloaded_variant = any(model == family or model.startswith(f"{family}:") for model in local_models)
            enriched.append(
                {
                    **item,
                    "has_downloaded_variant": has_downloaded_variant,
                    "selected": current_model == family,
                }
            )
        return {
            "query": q,
            "page": page,
            "items": enriched,
        }

    @app.get("/api/model-library/{family}/tags")
    def list_model_tags(family: str) -> dict[str, Any]:
        if agent.config.llm_provider != "ollama":
            raise HTTPException(status_code=400, detail="当前提供方不支持标签版本列表，请切换到 Ollama。")
        try:
            items = agent.list_model_tags(family)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        runtime_info = agent.runtime_metadata
        local_models = set(runtime_info["available_models"])
        current_model = runtime_info["model"]
        if not items:
            family_prefix = f"{family}:"
            local_items = [name for name in sorted(local_models) if name == family or name.startswith(family_prefix)]
            items = [
                {
                    "name": name,
                    "variant": name.split(":", 1)[1] if ":" in name else "latest",
                    "family": family,
                }
                for name in local_items
            ]
        return {
            "family": family,
            "items": [
                {
                    **item,
                    "downloaded": item["name"] in local_models,
                    "selected": item["name"] == current_model,
                }
                for item in items
            ],
        }

    @app.post("/api/models/select")
    def select_model(payload: SelectModelPayload) -> dict[str, Any]:
        try:
            runtime_info = agent.select_model(payload.model)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"runtime": runtime_info}

    @app.post("/api/models/pull")
    def pull_model(payload: PullModelPayload) -> StreamingResponse:
        model_name = payload.model.strip()
        if not model_name:
            raise HTTPException(status_code=400, detail="模型名称不能为空。")

        saved_auto_select = _parse_bool(agent.memory.get_setting("auto_select_after_pull"), True)
        should_select_after_pull = payload.select_after_pull if payload.select_after_pull is not None else saved_auto_select
        configured_models_dir = (agent.memory.get_setting("ollama_models_dir") or "").strip()
        if configured_models_dir:
            os.environ["OLLAMA_MODELS"] = configured_models_dir

        def generate():
            try:
                yield _ndjson(
                    {
                        "type": "start",
                        "model": model_name,
                        "target_dir": configured_models_dir,
                    }
                )
                for event in agent.pull_model_stream(model_name):
                    yield _ndjson({"type": "progress", **event})
                runtime_info = agent.runtime_metadata
                if should_select_after_pull:
                    runtime_info = agent.select_model(model_name)
                yield _ndjson(
                    {
                        "type": "done",
                        "model": model_name,
                        "runtime": runtime_info,
                    }
                )
            except RuntimeError as exc:
                yield _ndjson({"type": "error", "detail": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive
                yield _ndjson({"type": "error", "detail": f"Server exception: {exc}"})

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/runtime")
    def runtime() -> dict[str, Any]:
        runtime_info = agent.runtime_metadata
        return {
            "runtime": runtime_info,
            "defaults": {
                "db_path": str(config.db_path),
                "intent_confidence_threshold": config.intent_confidence_threshold,
                "llm_history_limit": config.llm_history_limit,
            },
        }

    @app.post("/api/uploads")
    async def upload_file(file: UploadFile = File(...)) -> dict[str, Any]:
        filename = _normalize_upload_filename(file.filename)
        raw_bytes = await file.read(MAX_UPLOAD_FILE_BYTES + 1)
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="上传失败：文件为空。")
        if len(raw_bytes) > MAX_UPLOAD_FILE_BYTES:
            raise HTTPException(status_code=400, detail="上传失败：单个文件不能超过 2MB。")

        text, truncated = _extract_upload_text(filename, raw_bytes)
        upload_id = uuid4().hex
        suffix = Path(filename).suffix.lower() or ".txt"
        target_path = app.state.upload_dir / f"{upload_id}{suffix}"
        target_path.write_bytes(raw_bytes)

        content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        record = {
            "id": upload_id,
            "name": filename,
            "size": len(raw_bytes),
            "content_type": content_type,
            "content": text,
            "truncated": truncated,
            "saved_path": str(target_path),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        app.state.upload_store[upload_id] = record
        return {
            "upload": {
                "id": upload_id,
                "name": filename,
                "size": len(raw_bytes),
                "content_type": content_type,
                "truncated": truncated,
                "created_at": record["created_at"],
            }
        }

    @app.delete("/api/uploads/{upload_id}")
    def delete_upload(upload_id: str) -> dict[str, Any]:
        item = app.state.upload_store.pop(upload_id, None)
        if item and item.get("saved_path"):
            try:
                Path(str(item["saved_path"])).unlink(missing_ok=True)
            except OSError:
                pass
        return {"deleted": True}

    @app.get("/api/skills")
    def list_skills() -> dict[str, Any]:
        items = agent.memory.list_skills(limit=200)
        return {
            "items": [_skill_to_dict(item) for item in items],
            "defaults": {
                "empty_keywords_mode": "always_on",
            },
        }

    @app.post("/api/skills")
    def create_skill(payload: SkillPayload) -> dict[str, Any]:
        skill = agent.memory.create_skill(
            name=payload.name,
            description=payload.description,
            instruction=payload.instruction,
            trigger_keywords=_split_keywords(payload.trigger_keywords),
            enabled=payload.enabled,
        )
        return {"skill": _skill_to_dict(skill)}

    @app.put("/api/skills/{skill_id}")
    def update_skill(skill_id: str, payload: SkillPayload) -> dict[str, Any]:
        skill = agent.memory.update_skill(
            skill_id,
            name=payload.name,
            description=payload.description,
            instruction=payload.instruction,
            trigger_keywords=_split_keywords(payload.trigger_keywords),
            enabled=payload.enabled,
        )
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found.")
        return {"skill": _skill_to_dict(skill)}

    @app.patch("/api/skills/{skill_id}/toggle")
    def toggle_skill(skill_id: str, payload: SkillTogglePayload) -> dict[str, Any]:
        skill = agent.memory.set_skill_enabled(skill_id, payload.enabled)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found.")
        return {"skill": _skill_to_dict(skill)}

    @app.delete("/api/skills/{skill_id}")
    def delete_skill(skill_id: str) -> dict[str, Any]:
        ok = agent.memory.delete_skill(skill_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Skill not found.")
        return {"deleted": True}

    @app.get("/api/conversations")
    def list_conversations() -> dict[str, Any]:
        items = orchestrator.list_conversations(limit=100)
        return {"items": [_conversation_to_dict(item) for item in items]}

    @app.post("/api/conversations")
    def create_conversation(payload: CreateConversationPayload) -> dict[str, Any]:
        conversation = orchestrator.create_conversation(title=payload.title)
        return {"conversation": _conversation_to_dict(conversation)}

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(conversation_id: str) -> dict[str, Any]:
        conversation = orchestrator.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return {"conversation": _conversation_to_dict(conversation)}

    @app.patch("/api/conversations/{conversation_id}")
    def rename_conversation(conversation_id: str, payload: RenameConversationPayload) -> dict[str, Any]:
        ok = orchestrator.rename_conversation(conversation_id, payload.title)
        if not ok:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        conversation = orchestrator.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return {"conversation": _conversation_to_dict(conversation)}

    @app.delete("/api/conversations/{conversation_id}")
    def delete_conversation(conversation_id: str) -> dict[str, Any]:
        ok = orchestrator.delete_conversation(conversation_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return {"deleted": True}

    @app.get("/api/conversations/{conversation_id}/messages")
    def list_messages(conversation_id: str) -> dict[str, Any]:
        conversation = orchestrator.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        messages = orchestrator.list_messages(conversation_id, limit=400)
        return {
            "conversation": _conversation_to_dict(conversation),
            "items": [_message_to_dict(item) for item in messages],
        }

    @app.post("/api/conversations/{conversation_id}/messages")
    def send_message(conversation_id: str, payload: SendMessagePayload) -> dict[str, Any]:
        text = payload.content.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        uploads = _resolve_upload_records(payload.upload_ids, app.state.upload_store)
        upload_names = [item["name"] for item in uploads]
        message_for_store = text
        model_input = text
        if upload_names:
            message_for_store = f"{text}\n\n[附件] {'，'.join(upload_names)}"
            attachment_context = _build_upload_prompt_context(uploads)
            model_input = f"{text}\n\n{attachment_context}" if attachment_context else text
        try:
            user_message, assistant_message = orchestrator.send_message(
                conversation_id,
                message_for_store,
                model_override=payload.model,
                model_input=model_input,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        _cleanup_upload_records([item["id"] for item in uploads], app.state.upload_store)

        conversation = orchestrator.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return {
            "conversation": _conversation_to_dict(conversation),
            "user_message": _message_to_dict(user_message),
            "assistant_message": _message_to_dict(assistant_message),
            "used_uploads": [
                {"id": item["id"], "name": item["name"], "size": item["size"], "truncated": item["truncated"]}
                for item in uploads
            ],
        }

    @app.post("/api/conversations/{conversation_id}/messages/stream")
    def stream_message(conversation_id: str, payload: SendMessagePayload) -> StreamingResponse:
        text = payload.content.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        uploads = _resolve_upload_records(payload.upload_ids, app.state.upload_store)
        upload_names = [item["name"] for item in uploads]
        message_for_store = text
        model_input = text
        if upload_names:
            message_for_store = f"{text}\n\n[附件] {'，'.join(upload_names)}"
            attachment_context = _build_upload_prompt_context(uploads)
            model_input = f"{text}\n\n{attachment_context}" if attachment_context else text

        def generate():
            try:
                for event in orchestrator.stream_message(
                    conversation_id,
                    message_for_store,
                    model_override=payload.model,
                    model_input=model_input,
                ):
                    if event["type"] == "ack":
                        event_payload = {
                            "type": "ack",
                            "user_message": _message_to_dict(event["user_message"]),
                        }
                    elif event["type"] == "chunk":
                        event_payload = {
                            "type": "chunk",
                            "content": event["content"],
                        }
                    elif event["type"] == "done":
                        conversation = event["conversation"]
                        event_payload = {
                            "type": "done",
                            "assistant_message": _message_to_dict(event["assistant_message"]),
                            "conversation": _conversation_to_dict(conversation) if conversation else None,
                        }
                    else:
                        continue
                    yield _ndjson(event_payload)
                _cleanup_upload_records([item["id"] for item in uploads], app.state.upload_store)
            except ValueError as exc:
                yield _ndjson({"type": "error", "detail": str(exc)})
            except RuntimeError as exc:
                yield _ndjson({"type": "error", "detail": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive
                yield _ndjson({"type": "error", "detail": f"Server exception: {exc}"})

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    return app


app = create_app()


def run() -> None:
    host = (os.getenv("AURORA_WEB_HOST", "127.0.0.1") or "127.0.0.1").strip() or "127.0.0.1"

    preferred_port = 8000
    env_port_raw = (os.getenv("AURORA_WEB_PORT", "") or "").strip()
    if env_port_raw:
        try:
            preferred_port = int(env_port_raw)
        except ValueError:
            preferred_port = 8000
    else:
        # Fall back to persisted preference when launcher does not inject the env var.
        try:
            saved = app.state.agent.memory.get_setting("web_port_preferred")
            if saved and str(saved).strip():
                preferred_port = int(str(saved).strip())
        except Exception:
            preferred_port = 8000

    preferred_port = max(1000, min(65535, preferred_port))
    selected_port = _find_available_port(host, preferred_port, span=40)

    if selected_port != preferred_port:
        print(
            f"[WARN] Port {preferred_port} is busy. Falling back to {selected_port}. "
            "You can close the old process or update preferred port in settings."
        )

    os.environ["AURORA_WEB_PORT"] = str(selected_port)
    uvicorn.run("ai_agent.web.app:app", host=host, port=selected_port, reload=False)


if __name__ == "__main__":
    run()
