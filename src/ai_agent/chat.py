from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .agent import AIAgent
from .models import ChatMessage, Conversation


@dataclass(slots=True)
class PreparedMessage:
    conversation: Conversation
    user_message: ChatMessage
    history: list[dict[str, str]]
    model_content: str


class ChatOrchestrator:
    def __init__(self, agent: AIAgent):
        self.agent = agent
        self.memory = agent.memory

    def create_conversation(self, title: str | None = None) -> Conversation:
        return self.memory.create_conversation(title=title)

    def list_conversations(self, *, limit: int = 100) -> list[Conversation]:
        return self.memory.list_conversations(limit=limit)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.memory.get_conversation(conversation_id)

    def rename_conversation(self, conversation_id: str, title: str) -> bool:
        return self.memory.rename_conversation(conversation_id, title)

    def delete_conversation(self, conversation_id: str) -> bool:
        return self.memory.delete_conversation(conversation_id)

    def list_messages(self, conversation_id: str, *, limit: int = 300) -> list[ChatMessage]:
        return self.memory.list_conversation_messages(conversation_id, limit=limit)

    def send_message(
        self,
        conversation_id: str,
        content: str,
        *,
        model_override: str | None = None,
        model_input: str | None = None,
    ) -> tuple[ChatMessage, ChatMessage]:
        prepared = self._prepare_message(conversation_id, content, model_input=model_input)
        assistant_content = self.agent.handle_chat_message(
            message=prepared.model_content,
            history=prepared.history,
            model_override=model_override,
        )
        assistant_message = self._store_assistant_message(prepared.conversation.id, assistant_content)
        return prepared.user_message, assistant_message

    def stream_message(
        self,
        conversation_id: str,
        content: str,
        *,
        model_override: str | None = None,
        model_input: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        prepared = self._prepare_message(conversation_id, content, model_input=model_input)
        yield {"type": "ack", "user_message": prepared.user_message}

        chunks: list[str] = []
        for piece in self.agent.stream_chat_message(
            message=prepared.model_content,
            history=prepared.history,
            model_override=model_override,
        ):
            chunks.append(piece)
            yield {"type": "chunk", "content": piece}

        assistant_content = "".join(chunks).strip()
        if not assistant_content:
            assistant_content = "模型没有返回内容，请重试。"
        assistant_message = self._store_assistant_message(prepared.conversation.id, assistant_content)
        conversation = self.memory.get_conversation(prepared.conversation.id)
        yield {
            "type": "done",
            "assistant_message": assistant_message,
            "conversation": conversation,
        }

    def _prepare_message(self, conversation_id: str, content: str, *, model_input: str | None = None) -> PreparedMessage:
        normalized = content.strip()
        normalized_model = (model_input or content).strip()
        if not normalized:
            raise ValueError("Message content is empty.")
        if not normalized_model:
            raise ValueError("Model message content is empty.")

        conversation = self.memory.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError("Conversation not found.")

        history = [
            {"role": item.role, "content": item.content}
            for item in self.memory.list_conversation_messages(
                conversation_id,
                limit=self.agent.config.llm_history_limit,
            )
            if item.role in {"user", "assistant"} and item.content
        ]

        user_message_id = self.memory.add_conversation_message(
            conversation_id=conversation_id,
            role="user",
            content=normalized,
        )
        user_message = self._find_message_by_id(conversation_id, user_message_id)
        if user_message is None:
            raise RuntimeError("Saved user message but failed to load it.")

        return PreparedMessage(
            conversation=conversation,
            user_message=user_message,
            history=history,
            model_content=normalized_model,
        )

    def _store_assistant_message(self, conversation_id: str, content: str) -> ChatMessage:
        assistant_message_id = self.memory.add_conversation_message(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
        )
        assistant_message = self._find_message_by_id(conversation_id, assistant_message_id)
        if assistant_message is None:
            raise RuntimeError("Saved assistant message but failed to load it.")
        return assistant_message

    def _find_message_by_id(self, conversation_id: str, message_id: int) -> ChatMessage | None:
        recent = self.memory.list_conversation_messages(conversation_id, limit=30)
        return next((item for item in recent if item.id == message_id), None)
