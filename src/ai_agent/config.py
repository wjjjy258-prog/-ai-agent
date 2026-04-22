from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_LLM_PROVIDERS = {"ollama", "openai_compatible"}
PROVIDER_ALIASES = {
    "ollama": "ollama",
    "openai_compatible": "openai_compatible",
    "openai-compatible": "openai_compatible",
    "openai": "openai_compatible",
    "dashscope": "openai_compatible",
    "bailian": "openai_compatible",
    "aliyun": "openai_compatible",
}


def normalize_llm_provider(raw: str | None, default: str = "ollama") -> str:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if not normalized:
        return default
    mapped = PROVIDER_ALIASES.get(normalized, normalized)
    if mapped in SUPPORTED_LLM_PROVIDERS:
        return mapped
    return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"1", "true", "yes", "on", "y"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


@dataclass(slots=True)
class AgentConfig:
    db_path: Path
    max_list_items: int = 20
    default_daily_hours: float = 8.0

    enable_llm_chat: bool = True
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_timeout_sec: int = 120
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_model: str = "qwen-plus"
    openai_api_key: str = ""
    openai_timeout_sec: int = 120
    llm_history_limit: int = 20
    intent_confidence_threshold: float = 0.72

    @classmethod
    def from_db_path(cls, db_path: str | Path) -> "AgentConfig":
        path = Path(db_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(
            db_path=path,
            max_list_items=_env_int("AURORA_MAX_LIST_ITEMS", 20),
            default_daily_hours=_env_float("AURORA_DEFAULT_DAILY_HOURS", 8.0),
            enable_llm_chat=_env_bool("AURORA_ENABLE_LLM_CHAT", True),
            llm_provider=normalize_llm_provider(os.getenv("AURORA_LLM_PROVIDER", "ollama"), "ollama"),
            ollama_base_url=os.getenv("AURORA_OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip(),
            ollama_model=os.getenv("AURORA_OLLAMA_MODEL", "qwen3.5:4b").strip(),
            ollama_timeout_sec=_env_int("AURORA_OLLAMA_TIMEOUT_SEC", 120),
            openai_base_url=os.getenv(
                "AURORA_OPENAI_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ).strip(),
            openai_model=os.getenv("AURORA_OPENAI_MODEL", "qwen-plus").strip(),
            openai_api_key=os.getenv("AURORA_OPENAI_API_KEY", "").strip(),
            openai_timeout_sec=_env_int("AURORA_OPENAI_TIMEOUT_SEC", 120),
            llm_history_limit=_env_int("AURORA_LLM_HISTORY_LIMIT", 20),
            intent_confidence_threshold=_env_float("AURORA_INTENT_CONFIDENCE_THRESHOLD", 0.72),
        )
