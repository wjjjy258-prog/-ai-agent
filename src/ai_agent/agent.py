from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path

from .config import (
    AgentConfig,
    PROVIDER_ALIASES,
    SUPPORTED_LLM_PROVIDERS,
    normalize_llm_provider,
)
from .llm import ChatMessagePayload, OllamaLLMClient, build_llm_client
from .memory import SQLiteMemoryStore
from .models import IntentType, ParsedIntent
from .planner import IntentParser, OfflinePlanningBrain
from .tools import ToolRegistry, build_default_registry


class AIAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.memory = SQLiteMemoryStore(config.db_path)
        self.parser = IntentParser()
        self.brain = OfflinePlanningBrain()
        self.registry: ToolRegistry = build_default_registry(self.memory, self.config)
        self.llm = build_llm_client(config)
        self._exit_requested = False
        self._hydrate_runtime_settings()

    @property
    def should_exit(self) -> bool:
        return self._exit_requested

    @property
    def runtime_metadata(self) -> dict:
        available_models: list[str] = []
        reachable = False
        try:
            available_models = self.llm.list_models()
            reachable = True
        except Exception:
            reachable = False

        provider = normalize_llm_provider(self.llm.provider or self.config.llm_provider, "ollama")
        current_model = (self.llm.model or self._model_for_provider(provider)).strip()
        current_base_url = (self.llm.base_url or self._base_url_for_provider(provider)).strip()
        models_dir = os.getenv("OLLAMA_MODELS", "").strip() if provider == "ollama" else ""
        enabled_skills = self.memory.list_skills(enabled_only=True, limit=200)
        total_skills = self.memory.list_skills(limit=200)
        return {
            "llm_enabled": self.config.enable_llm_chat,
            "provider": provider,
            "model": current_model,
            "base_url": current_base_url,
            "models_dir": models_dir,
            "reachable": reachable,
            "available_models": available_models,
            "supports_model_pull": bool(self.llm.supports_model_pull),
            "openai_api_key_configured": bool(self.config.openai_api_key.strip()),
            "enabled_skills": len(enabled_skills),
            "skill_count": len(total_skills),
        }

    def handle_message(self, message: str) -> str:
        return self.handle_chat_message(message=message, history=[])

    def handle_chat_message(
        self,
        *,
        message: str,
        history: list[dict[str, str]] | None = None,
        model_override: str | None = None,
    ) -> str:
        cleaned = message.strip()
        if not cleaned:
            return "发送前请输入内容。"

        self.memory.record_interaction("user", cleaned)
        intent = self.parser.parse(cleaned)

        if self._should_execute_tool(intent):
            final = self._execute_intent(intent)
        else:
            final = self._chat_with_llm(user_message=cleaned, history=history or [], model_override=model_override)

        self.memory.record_interaction("assistant", final)
        return final

    def stream_chat_message(
        self,
        *,
        message: str,
        history: list[dict[str, str]] | None = None,
        model_override: str | None = None,
    ) -> Iterator[str]:
        cleaned = message.strip()
        if not cleaned:
            final = "发送前请输入内容。"
            self.memory.record_interaction("assistant", final)
            yield final
            return

        self.memory.record_interaction("user", cleaned)
        intent = self.parser.parse(cleaned)

        if self._should_execute_tool(intent):
            final = self._execute_intent(intent)
            self.memory.record_interaction("assistant", final)
            yield final
            return

        prompt = self._build_system_prompt(cleaned)
        chat_messages = self._build_chat_messages(history or [], cleaned)
        chunks: list[str] = []
        try:
            for piece in self.llm.chat_stream(
                system_prompt=prompt,
                messages=chat_messages,
                model_override=model_override,
            ):
                chunks.append(piece)
                yield piece
            final = "".join(chunks).strip()
            if not final:
                final = "模型没有返回内容，请重试。"
                yield final
        except Exception as exc:
            final = (
                "调用模型失败。\n"
                f"错误信息：{exc}\n"
                "你仍然可以使用内置命令，例如 `add task ...`、`daily plan 6 hours`、`weekly review`。"
            )
            yield final

        self.memory.record_interaction("assistant", final)

    def select_model(self, model_name: str, *, persist: bool = True) -> dict:
        cleaned = model_name.strip()
        if not cleaned:
            raise RuntimeError("模型名称不能为空。")
        provider = normalize_llm_provider(self.config.llm_provider, "ollama")
        self._set_model_for_provider(provider, cleaned)
        try:
            self.llm.set_model(cleaned)
        except NotImplementedError:
            pass
        if persist:
            self.memory.set_setting("default_model", cleaned)
            self.memory.set_setting(self._provider_model_key(provider), cleaned)
            if provider == "openai_compatible":
                self.memory.set_setting("openai_model", cleaned)
        return self.runtime_metadata

    def list_remote_models(self, *, query: str = "", page: int = 1) -> list[dict]:
        return self.llm.list_remote_models(query=query, page=page)

    def list_model_tags(self, family: str) -> list[dict]:
        return self.llm.list_model_tags(family)

    def pull_model_stream(self, model_name: str) -> Iterator[dict]:
        for event in self.llm.pull_model_stream(model_name):
            yield event

    def apply_runtime_settings(
        self,
        *,
        llm_provider: str | None = None,
        ollama_base_url: str | None = None,
        openai_base_url: str | None = None,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        llm_model: str | None = None,
        llm_history_limit: int | None = None,
        intent_confidence_threshold: float | None = None,
        ollama_models_dir: str | None = None,
    ) -> dict:
        llm_requires_rebuild = False
        pending_model_selection: str | None = None

        if llm_provider is not None:
            requested_provider = llm_provider.strip().lower()
            normalized_provider = normalize_llm_provider(llm_provider, self.config.llm_provider)
            if (
                requested_provider
                and requested_provider not in SUPPORTED_LLM_PROVIDERS
                and requested_provider not in PROVIDER_ALIASES
            ):
                raise RuntimeError(f"不支持的模型提供方：{llm_provider}")
            if normalized_provider != self.config.llm_provider:
                self.config.llm_provider = normalized_provider
                self.memory.set_setting("llm_provider", normalized_provider)
                llm_requires_rebuild = True

        if ollama_base_url is not None:
            cleaned_base_url = ollama_base_url.strip()
            if not cleaned_base_url:
                raise RuntimeError("Ollama 地址不能为空。")
            self.config.ollama_base_url = cleaned_base_url
            self.memory.set_setting("ollama_base_url", cleaned_base_url)
            if self.config.llm_provider == "ollama":
                llm_requires_rebuild = True

        if openai_base_url is not None:
            cleaned_base_url = openai_base_url.strip()
            if not cleaned_base_url:
                raise RuntimeError("API 地址不能为空。")
            self.config.openai_base_url = cleaned_base_url.rstrip("/")
            self.memory.set_setting("openai_base_url", self.config.openai_base_url)
            if self.config.llm_provider == "openai_compatible":
                llm_requires_rebuild = True

        if openai_api_key is not None:
            cleaned_api_key = openai_api_key.strip()
            self.config.openai_api_key = cleaned_api_key
            self.memory.set_setting("openai_api_key", cleaned_api_key)
            if self.config.llm_provider == "openai_compatible":
                llm_requires_rebuild = True

        if openai_model is not None:
            cleaned_openai_model = openai_model.strip()
            if not cleaned_openai_model:
                raise RuntimeError("API 默认模型不能为空。")
            self.config.openai_model = cleaned_openai_model
            self.memory.set_setting("openai_model", cleaned_openai_model)
            self.memory.set_setting(self._provider_model_key("openai_compatible"), cleaned_openai_model)
            self.memory.set_setting("default_model", cleaned_openai_model)
            if self.config.llm_provider == "openai_compatible":
                pending_model_selection = cleaned_openai_model

        if llm_history_limit is not None:
            clamped_limit = max(4, min(80, int(llm_history_limit)))
            self.config.llm_history_limit = clamped_limit
            self.memory.set_setting("llm_history_limit", str(clamped_limit))

        if intent_confidence_threshold is not None:
            threshold = max(0.05, min(0.98, float(intent_confidence_threshold)))
            self.config.intent_confidence_threshold = threshold
            self.memory.set_setting("intent_confidence_threshold", f"{threshold:.3f}")

        if ollama_models_dir is not None:
            cleaned_models_dir = ollama_models_dir.strip()
            if cleaned_models_dir:
                resolved_models_dir = str(Path(cleaned_models_dir).expanduser().resolve())
                Path(resolved_models_dir).mkdir(parents=True, exist_ok=True)
                os.environ["OLLAMA_MODELS"] = resolved_models_dir
                self.memory.set_setting("ollama_models_dir", resolved_models_dir)
            else:
                os.environ.pop("OLLAMA_MODELS", None)
                self.memory.set_setting("ollama_models_dir", "")

        if llm_model is not None:
            cleaned_model = llm_model.strip()
            if not cleaned_model:
                raise RuntimeError("模型名称不能为空。")
            pending_model_selection = cleaned_model

        if llm_requires_rebuild:
            self.llm = build_llm_client(self.config)
            self._apply_current_model_to_llm()

        if pending_model_selection:
            self.select_model(pending_model_selection)

        return self.runtime_metadata

    def _hydrate_runtime_settings(self) -> None:
        saved_provider = self.memory.get_setting("llm_provider")
        if saved_provider and saved_provider.strip():
            self.config.llm_provider = normalize_llm_provider(saved_provider, self.config.llm_provider)

        saved_base_url = self.memory.get_setting("ollama_base_url")
        if saved_base_url and saved_base_url.strip():
            self.config.ollama_base_url = saved_base_url.strip()

        saved_openai_base_url = self.memory.get_setting("openai_base_url")
        if saved_openai_base_url and saved_openai_base_url.strip():
            self.config.openai_base_url = saved_openai_base_url.strip().rstrip("/")

        saved_openai_api_key = self.memory.get_setting("openai_api_key")
        if saved_openai_api_key is not None:
            self.config.openai_api_key = saved_openai_api_key.strip()

        saved_openai_model = self.memory.get_setting("openai_model")
        if saved_openai_model and saved_openai_model.strip():
            self.config.openai_model = saved_openai_model.strip()

        saved_history_limit = self.memory.get_setting("llm_history_limit")
        if saved_history_limit:
            try:
                self.config.llm_history_limit = max(4, min(80, int(saved_history_limit.strip())))
            except ValueError:
                pass

        saved_intent_threshold = self.memory.get_setting("intent_confidence_threshold")
        if saved_intent_threshold:
            try:
                parsed = float(saved_intent_threshold.strip())
                self.config.intent_confidence_threshold = max(0.05, min(0.98, parsed))
            except ValueError:
                pass

        saved_models_dir = self.memory.get_setting("ollama_models_dir")
        if saved_models_dir and saved_models_dir.strip():
            os.environ["OLLAMA_MODELS"] = saved_models_dir.strip()

        self.llm = build_llm_client(self.config)

        provider = normalize_llm_provider(self.config.llm_provider, "ollama")
        saved_model = self.memory.get_setting(self._provider_model_key(provider))
        if not saved_model:
            saved_model = self.memory.get_setting("default_model")
        if saved_model:
            self.select_model(saved_model, persist=False)
        else:
            self._apply_current_model_to_llm()

    def _should_execute_tool(self, intent: ParsedIntent) -> bool:
        command_intents = {
            IntentType.CREATE_TASK,
            IntentType.LIST_TASKS,
            IntentType.COMPLETE_TASK,
            IntentType.POSTPONE_TASK,
            IntentType.ADD_NOTE,
            IntentType.SEARCH_NOTES,
            IntentType.DAILY_PLAN,
            IntentType.WEEKLY_REVIEW,
            IntentType.HELP,
            IntentType.EXIT,
        }
        if intent.intent in command_intents:
            return True
        return intent.confidence >= self.config.intent_confidence_threshold and intent.intent is not IntentType.UNKNOWN

    def _execute_intent(self, intent: ParsedIntent) -> str:
        plan = self.brain.create_plan(intent)
        replies: list[str] = []
        for step in plan:
            result = self.registry.execute(step.tool_name, step.args)
            replies.append(result.message)
            if result.data.get("exit"):
                self._exit_requested = True
        return "\n\n".join(replies)

    def _chat_with_llm(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]],
        model_override: str | None = None,
    ) -> str:
        prompt = self._build_system_prompt(user_message)
        chat_messages = self._build_chat_messages(history, user_message)
        try:
            return self.llm.chat(
                system_prompt=prompt,
                messages=chat_messages,
                model_override=model_override,
            )
        except Exception as exc:
            return (
                "调用模型失败。\n"
                f"错误信息：{exc}\n"
                "你仍然可以使用内置命令模式。"
            )

    def _build_chat_messages(self, history: list[dict[str, str]], user_message: str) -> list[ChatMessagePayload]:
        trimmed_history = history[-self.config.llm_history_limit :]
        chat_messages = [
            ChatMessagePayload(role=item["role"], content=item["content"])
            for item in trimmed_history
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]
        chat_messages.append(ChatMessagePayload(role="user", content=user_message))
        return chat_messages

    def _build_system_prompt(self, user_message: str) -> str:
        prompt = (
            "你是一个以中文为主的本地智能助手。默认使用中文回答。\n"
            "普通问题直接回答；涉及任务管理时，优先给出可执行步骤。\n"
            "不要编造事实；不确定时要明确说明。"
        )
        skills = self.memory.match_skills(user_message, limit=4)
        if not skills:
            return prompt

        sections = [prompt, "", "你还需要遵循以下已激活技能："]
        for skill in skills:
            sections.append(f"- 技能：{skill.name}")
            if skill.description:
                sections.append(f"  说明：{skill.description}")
            sections.append(f"  规则：{skill.instruction.strip()}")
        return "\n".join(sections)

    @staticmethod
    def _provider_model_key(provider: str) -> str:
        normalized = normalize_llm_provider(provider, "ollama")
        return f"default_model_{normalized}"

    def _model_for_provider(self, provider: str) -> str:
        normalized = normalize_llm_provider(provider, "ollama")
        if normalized == "openai_compatible":
            return self.config.openai_model
        return self.config.ollama_model

    def _set_model_for_provider(self, provider: str, model_name: str) -> None:
        normalized = normalize_llm_provider(provider, "ollama")
        if normalized == "openai_compatible":
            self.config.openai_model = model_name
            return
        self.config.ollama_model = model_name

    def _base_url_for_provider(self, provider: str) -> str:
        normalized = normalize_llm_provider(provider, "ollama")
        if normalized == "openai_compatible":
            return self.config.openai_base_url
        return self.config.ollama_base_url

    def _apply_current_model_to_llm(self) -> None:
        model_name = self._model_for_provider(self.config.llm_provider)
        try:
            self.llm.set_model(model_name)
        except NotImplementedError:
            return


def llm_is_ollama(agent: AIAgent) -> bool:
    return isinstance(agent.llm, OllamaLLMClient)
