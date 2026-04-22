from __future__ import annotations

import html
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import monotonic
from typing import Any, Iterator

from .config import AgentConfig, normalize_llm_provider


@dataclass(slots=True)
class ChatMessagePayload:
    role: str
    content: str


class BaseLLMClient(ABC):
    @property
    @abstractmethod
    def provider(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @property
    def base_url(self) -> str:
        return ""

    @property
    def supports_model_pull(self) -> bool:
        return False

    @abstractmethod
    def chat(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def chat_stream(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def is_reachable(self) -> bool:
        raise NotImplementedError

    def set_model(self, model_name: str) -> None:
        raise NotImplementedError

    def list_remote_models(self, *, query: str = "", page: int = 1) -> list[dict]:
        return []

    def list_model_tags(self, family: str) -> list[dict]:
        return []

    def pull_model_stream(self, model_name: str) -> Iterator[dict]:
        raise RuntimeError("Current provider does not support pulling models.")


class NullLLMClient(BaseLLMClient):
    def __init__(self, *, provider: str = "none", model: str = "none", base_url: str = ""):
        self._provider = provider.strip() or "none"
        self._model = model.strip() or "none"
        self._base_url = base_url.strip()

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def chat(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> str:
        raise RuntimeError("LLM chat is disabled.")

    def chat_stream(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> Iterator[str]:
        raise RuntimeError("LLM chat is disabled.")

    def list_models(self) -> list[str]:
        return []

    def is_reachable(self) -> bool:
        return False

    def set_model(self, model_name: str) -> None:
        cleaned = model_name.strip()
        if cleaned:
            self._model = cleaned


class OllamaLLMClient(BaseLLMClient):
    SEARCH_URL = "https://ollama.com/search"
    TAGS_URL_TEMPLATE = "https://registry.ollama.com/library/{family}/tags"
    REMOTE_MODELS_CACHE_TTL_SEC = 45.0
    MODEL_TAGS_CACHE_TTL_SEC = 180.0

    def __init__(self, *, base_url: str, model: str, timeout_sec: int = 120):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_sec = max(10, timeout_sec)
        self._remote_models_cache: dict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = {}
        self._model_tags_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    @property
    def provider(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def supports_model_pull(self) -> bool:
        return True

    def set_model(self, model_name: str) -> None:
        cleaned = model_name.strip()
        if cleaned:
            self._model = cleaned

    def resolve_model(self, model_override: str | None = None) -> str:
        if model_override and model_override.strip():
            return model_override.strip()
        return self._model

    def chat(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> str:
        payload = self._build_payload(
            system_prompt=system_prompt,
            messages=messages,
            model=self.resolve_model(model_override),
            stream=False,
        )
        response_body = self._request_json("/api/chat", payload)
        message = response_body.get("message") or {}
        content = str(message.get("content", "")).strip()
        if not content:
            raise RuntimeError("Ollama returned an empty response.")
        return content

    def chat_stream(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> Iterator[str]:
        payload = self._build_payload(
            system_prompt=system_prompt,
            messages=messages,
            model=self.resolve_model(model_override),
            stream=True,
        )
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self._base_url}/api/chat",
            method="POST",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_sec) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("error"):
                        raise RuntimeError(f"Ollama stream error: {item['error']}")
                    message = item.get("message") or {}
                    piece = str(message.get("content", ""))
                    if piece:
                        yield piece
                    if item.get("done"):
                        break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama connection failed: {exc.reason}") from exc
        except socket.timeout as exc:
            raise RuntimeError("Ollama request timed out.") from exc

    def list_models(self) -> list[str]:
        payload = self._request_json("/api/tags", None, method="GET")
        models = payload.get("models") or []
        result: list[str] = []
        for item in models:
            name = str(item.get("name", "")).strip()
            if name:
                result.append(name)
        return result

    def is_reachable(self) -> bool:
        try:
            _ = self.list_models()
            return True
        except Exception:
            return False

    def list_remote_models(self, *, query: str = "", page: int = 1) -> list[dict]:
        page_num = max(1, int(page))
        normalized_query = query.strip()
        cache_key = (normalized_query.lower(), page_num)
        cached = self._cache_get(self._remote_models_cache, cache_key, self.REMOTE_MODELS_CACHE_TTL_SEC)
        if cached is not None:
            return cached

        params = {"page": page_num}
        if normalized_query:
            params["q"] = normalized_query
        url = f"{self.SEARCH_URL}?{urllib.parse.urlencode(params)}"
        content = self._fetch_text(url)
        items: list[dict] = []
        seen: set[str] = set()
        for block in re.findall(r'<li[^>]*x-test-model[^>]*>(.*?)</li>', content, flags=re.S):
            href = self._extract_first(block, r'<a href="/library/([^"]+)"')
            if not href:
                continue
            family = href.strip()
            if family in seen or ":" in family:
                continue
            name = self._extract_first(block, r'<span[^>]*x-test-search-response-title[^>]*>(.*?)</span>') or family
            description = self._extract_first(block, r'<p class="max-w-lg[^>]*>(.*?)</p>')
            pulls = self._extract_first(block, r'<span[^>]*x-test-pull-count[^>]*>(.*?)</span>')
            tag_count = self._extract_first(block, r'<span[^>]*x-test-tag-count[^>]*>(.*?)</span>')
            updated = self._extract_first(block, r'<span[^>]*x-test-updated[^>]*>(.*?)</span>')
            capabilities = self._extract_many(block, r'<span[^>]*x-test-capability[^>]*>(.*?)</span>')
            sizes = self._extract_many(block, r'<span[^>]*x-test-size[^>]*>(.*?)</span>')
            items.append(
                {
                    "name": name,
                    "family": family,
                    "description": description,
                    "capabilities": capabilities,
                    "sizes": sizes,
                    "pull_count": pulls,
                    "tag_count": tag_count,
                    "updated": updated,
                    "link": f"https://ollama.com/library/{family}",
                }
            )
            seen.add(family)
        self._cache_set(self._remote_models_cache, cache_key, items)
        return items

    def list_model_tags(self, family: str) -> list[dict]:
        normalized_family = family.strip()
        if not normalized_family:
            return []
        cache_key = normalized_family.lower()
        cached = self._cache_get(self._model_tags_cache, cache_key, self.MODEL_TAGS_CACHE_TTL_SEC)
        if cached is not None:
            return cached

        url = self.TAGS_URL_TEMPLATE.format(family=urllib.parse.quote(normalized_family, safe=""))
        content = self._fetch_text(url)
        found = re.findall(r'<a href="/library/([^"]+)"', content)
        items: list[dict] = []
        seen: set[str] = set()
        prefix = f"{normalized_family}:"
        for raw_name in found:
            full_name = html.unescape(raw_name.strip())
            if not full_name.startswith(prefix):
                continue
            if full_name in seen:
                continue
            items.append(
                {
                    "name": full_name,
                    "variant": full_name.split(":", 1)[1],
                    "family": normalized_family,
                }
            )
            seen.add(full_name)
        self._cache_set(self._model_tags_cache, cache_key, items)
        return items

    def pull_model_stream(self, model_name: str) -> Iterator[dict]:
        cleaned = model_name.strip()
        if not cleaned:
            raise RuntimeError("Model name is empty.")

        body = json.dumps({"model": cleaned, "stream": True}).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self._base_url}/api/pull",
            method="POST",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        timeout = max(self._timeout_sec, 600)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("error"):
                        raise RuntimeError(f"Ollama pull error: {item['error']}")
                    completed = int(item.get("completed") or 0)
                    total = int(item.get("total") or 0)
                    percent = round(completed * 100 / total, 1) if total > 0 else None
                    yield {
                        "model": cleaned,
                        "status": str(item.get("status", "")).strip() or "pulling",
                        "digest": str(item.get("digest", "")).strip(),
                        "completed": completed,
                        "total": total,
                        "percent": percent,
                    }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama connection failed: {exc.reason}") from exc
        except socket.timeout as exc:
            raise RuntimeError("Ollama pull timed out.") from exc

    def _build_payload(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model: str,
        stream: bool,
    ) -> dict:
        serialized_messages = [{"role": "system", "content": system_prompt}]
        serialized_messages.extend({"role": item.role, "content": item.content} for item in messages)
        return {
            "model": model,
            "messages": serialized_messages,
            "stream": stream,
            "options": {
                "temperature": 0.5,
            },
        }

    def _fetch_text(self, url: str) -> str:
        request = urllib.request.Request(url=url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=max(self._timeout_sec, 30)) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Remote model library error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Remote model library connection failed: {exc.reason}") from exc
        except socket.timeout as exc:
            raise RuntimeError("Remote model library request timed out.") from exc

    def _request_json(self, path: str, payload: dict | None, method: str = "POST") -> dict:
        data: bytes | None = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url=f"{self._base_url}{path}",
            method=method,
            data=data,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_sec) as response:
                response_body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama connection failed: {exc.reason}") from exc
        except socket.timeout as exc:
            raise RuntimeError("Ollama request timed out.") from exc

        try:
            return json.loads(response_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned invalid JSON response.") from exc

    @staticmethod
    def _extract_first(content: str, pattern: str) -> str:
        match = re.search(pattern, content, flags=re.S)
        if not match:
            return ""
        return OllamaLLMClient._clean_html(match.group(1))

    @staticmethod
    def _extract_many(content: str, pattern: str) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for raw in re.findall(pattern, content, flags=re.S):
            cleaned = OllamaLLMClient._clean_html(raw)
            if not cleaned or cleaned in seen:
                continue
            values.append(cleaned)
            seen.add(cleaned)
        return values

    @staticmethod
    def _clean_html(value: str) -> str:
        cleaned = re.sub(r"<[^>]+>", "", value)
        return html.unescape(" ".join(cleaned.split())).strip()

    @staticmethod
    def _clone_records(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [dict(item) for item in items]

    def _cache_get(
        self,
        cache: dict[Any, tuple[float, list[dict[str, Any]]]],
        key: Any,
        ttl_sec: float,
    ) -> list[dict[str, Any]] | None:
        item = cache.get(key)
        if item is None:
            return None
        stored_at, payload = item
        if monotonic() - stored_at > ttl_sec:
            cache.pop(key, None)
            return None
        return self._clone_records(payload)

    def _cache_set(
        self,
        cache: dict[Any, tuple[float, list[dict[str, Any]]]],
        key: Any,
        value: list[dict[str, Any]],
    ) -> None:
        cache[key] = (monotonic(), self._clone_records(value))


class OpenAICompatibleLLMClient(BaseLLMClient):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_sec: int = 120,
        provider_name: str = "openai_compatible",
    ):
        cleaned_base_url = base_url.strip().rstrip("/")
        self._base_url = cleaned_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._api_key = api_key.strip()
        self._model = model.strip() or "qwen-plus"
        self._timeout_sec = max(10, timeout_sec)
        self._provider_name = provider_name.strip() or "openai_compatible"

    @property
    def provider(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def set_model(self, model_name: str) -> None:
        cleaned = model_name.strip()
        if cleaned:
            self._model = cleaned

    def resolve_model(self, model_override: str | None = None) -> str:
        if model_override and model_override.strip():
            return model_override.strip()
        return self._model

    def chat(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> str:
        payload = self._build_payload(
            system_prompt=system_prompt,
            messages=messages,
            model=self.resolve_model(model_override),
            stream=False,
        )
        response = self._request_json("/chat/completions", payload, method="POST")
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI-compatible endpoint returned an empty response.")
        message = choices[0].get("message") or {}
        content = self._extract_text(message.get("content"))
        if not content:
            content = self._extract_text(choices[0].get("text"))
        if not content:
            raise RuntimeError("OpenAI-compatible endpoint returned an empty response.")
        return content

    def chat_stream(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model_override: str | None = None,
    ) -> Iterator[str]:
        payload = self._build_payload(
            system_prompt=system_prompt,
            messages=messages,
            model=self.resolve_model(model_override),
            stream=True,
        )
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self._base_url}/chat/completions",
            method="POST",
            data=body,
            headers={
                "Content-Type": "application/json",
                **self._auth_headers(),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_sec) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    if data == "[DONE]":
                        break
                    try:
                        item = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if item.get("error"):
                        raise RuntimeError(f"OpenAI-compatible stream error: {item['error']}")

                    for choice in item.get("choices") or []:
                        delta = choice.get("delta") or {}
                        piece = self._extract_text(delta.get("content"))
                        if piece:
                            yield piece
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible connection failed: {exc.reason}") from exc
        except socket.timeout as exc:
            raise RuntimeError("OpenAI-compatible request timed out.") from exc

    def list_models(self) -> list[str]:
        payload = self._request_json("/models", None, method="GET")
        models: list[str] = []
        for item in payload.get("data") or []:
            model_name = str(item.get("id", "")).strip()
            if model_name:
                models.append(model_name)
        return sorted(set(models), key=str.lower)

    def is_reachable(self) -> bool:
        try:
            _ = self.list_models()
            return True
        except Exception:
            return False

    def list_remote_models(self, *, query: str = "", page: int = 1) -> list[dict]:
        items = self.list_models()
        normalized_query = query.strip().lower()
        if normalized_query:
            items = [name for name in items if normalized_query in name.lower()]

        page_size = 50
        page_num = max(1, int(page))
        start = (page_num - 1) * page_size
        end = start + page_size

        result: list[dict] = []
        for name in items[start:end]:
            result.append(
                {
                    "name": name,
                    "family": name,
                    "description": "来自当前 API 提供方的可用模型列表",
                    "capabilities": [],
                    "sizes": [],
                    "pull_count": "",
                    "tag_count": "",
                    "updated": "",
                    "link": "",
                }
            )
        return result

    def pull_model_stream(self, model_name: str) -> Iterator[dict]:
        raise RuntimeError("Current provider does not support local model pull.")

    def _auth_headers(self) -> dict[str, str]:
        if not self._api_key:
            raise RuntimeError("API Key is empty. Please set API Key in settings first.")
        return {"Authorization": f"Bearer {self._api_key}"}

    def _build_payload(
        self,
        *,
        system_prompt: str,
        messages: list[ChatMessagePayload],
        model: str,
        stream: bool,
    ) -> dict[str, Any]:
        serialized_messages = [{"role": "system", "content": system_prompt}]
        serialized_messages.extend({"role": item.role, "content": item.content} for item in messages)
        return {
            "model": model,
            "messages": serialized_messages,
            "stream": stream,
            "temperature": 0.5,
        }

    def _request_json(self, path: str, payload: dict | None, *, method: str = "POST") -> dict:
        data: bytes | None = None
        headers = {"Content-Type": "application/json"}
        headers.update(self._auth_headers())
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self._base_url}{path}",
            method=method,
            data=data,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_sec) as response:
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible connection failed: {exc.reason}") from exc
        except socket.timeout as exc:
            raise RuntimeError("OpenAI-compatible request timed out.") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI-compatible endpoint returned invalid JSON.") from exc

    @staticmethod
    def _extract_text(content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            pieces: list[str] = []
            for item in content:
                if isinstance(item, str):
                    if item.strip():
                        pieces.append(item.strip())
                    continue
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    pieces.append(text.strip())
                    continue
                alt = item.get("content")
                if isinstance(alt, str) and alt.strip():
                    pieces.append(alt.strip())
            return "".join(pieces).strip()
        if isinstance(content, dict):
            text = content.get("text")
            if isinstance(text, str):
                return text.strip()
            return ""
        return str(content).strip()


def _model_for_provider(config: AgentConfig, provider: str) -> str:
    if provider == "openai_compatible":
        return config.openai_model
    return config.ollama_model


def _base_url_for_provider(config: AgentConfig, provider: str) -> str:
    if provider == "openai_compatible":
        return config.openai_base_url
    return config.ollama_base_url


def build_llm_client(config: AgentConfig) -> BaseLLMClient:
    provider = normalize_llm_provider(config.llm_provider, "ollama")
    config.llm_provider = provider

    if not config.enable_llm_chat:
        return NullLLMClient(
            provider=provider,
            model=_model_for_provider(config, provider),
            base_url=_base_url_for_provider(config, provider),
        )

    if provider == "ollama":
        return OllamaLLMClient(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout_sec=config.ollama_timeout_sec,
        )

    if provider == "openai_compatible":
        return OpenAICompatibleLLMClient(
            base_url=config.openai_base_url,
            api_key=config.openai_api_key,
            model=config.openai_model,
            timeout_sec=config.openai_timeout_sec,
        )

    return NullLLMClient()
