from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    TODO = "todo"
    DONE = "done"


class IntentType(str, Enum):
    CREATE_TASK = "create_task"
    LIST_TASKS = "list_tasks"
    COMPLETE_TASK = "complete_task"
    POSTPONE_TASK = "postpone_task"
    ADD_NOTE = "add_note"
    SEARCH_NOTES = "search_notes"
    DAILY_PLAN = "daily_plan"
    WEEKLY_REVIEW = "weekly_review"
    HELP = "help"
    EXIT = "exit"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Task:
    id: int
    title: str
    description: str
    priority: Priority
    status: TaskStatus
    due_date: str | None
    estimate_hours: float | None
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None


@dataclass(slots=True)
class Note:
    id: int
    content: str
    topic: str
    tags: list[str]
    created_at: str


@dataclass(slots=True)
class Conversation:
    id: str
    title: str
    created_at: str
    updated_at: str
    last_message_preview: str = ""
    message_count: int = 0


@dataclass(slots=True)
class ChatMessage:
    id: int
    conversation_id: str
    role: str
    content: str
    created_at: str


@dataclass(slots=True)
class Skill:
    id: str
    name: str
    description: str
    instruction: str
    trigger_keywords: list[str]
    enabled: bool
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ParsedIntent:
    intent: IntentType
    args: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    raw_text: str = ""


@dataclass(slots=True)
class PlanStep:
    tool_name: str
    args: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""


@dataclass(slots=True)
class ExecutionResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
