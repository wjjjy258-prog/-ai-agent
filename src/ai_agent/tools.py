from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from .config import AgentConfig
from .memory import SQLiteMemoryStore
from .models import ExecutionResult, Note, Priority, Task, TaskStatus
from .utils import normalize_tags, parse_natural_date, parse_priority, parse_status, safe_float


ToolHandler = Callable[[dict], ExecutionResult]


@dataclass(slots=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda t: t.name)

    def execute(self, tool_name: str, args: dict) -> ExecutionResult:
        tool = self._tools.get(tool_name)
        if tool is None:
            return ExecutionResult(success=False, message=f"Tool not found: {tool_name}")
        try:
            return tool.handler(args)
        except Exception as exc:  # pragma: no cover - defensive guard
            return ExecutionResult(success=False, message=f"Tool execution failed: {exc}")


class AgentTools:
    def __init__(self, memory: SQLiteMemoryStore, config: AgentConfig):
        self.memory = memory
        self.config = config

    def create_task(self, args: dict) -> ExecutionResult:
        title = str(args.get("title", "")).strip()
        if not title:
            return ExecutionResult(success=False, message="Create task failed: missing title.")

        description = str(args.get("description", "")).strip()
        priority = parse_priority(str(args.get("priority", "")) or None, default=Priority.MEDIUM)
        due_date = parse_natural_date(args.get("due_date"))
        estimate_hours = safe_float(args.get("estimate_hours"))
        tags = normalize_tags(args.get("tags"))

        task_id = self.memory.add_task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            estimate_hours=estimate_hours,
            tags=tags,
        )
        details = [
            f"Task created. ID: {task_id}",
            f"Title: {title}",
            f"Priority: {priority.value}",
        ]
        if due_date:
            details.append(f"Due date: {due_date}")
        if estimate_hours is not None:
            details.append(f"Estimate: {estimate_hours:.1f}h")
        if tags:
            details.append(f"Tags: {', '.join(tags)}")
        return ExecutionResult(success=True, message="\n".join(details), data={"task_id": task_id})

    def list_tasks(self, args: dict) -> ExecutionResult:
        status = parse_status(args.get("status"))
        keyword = str(args.get("keyword", "")).strip() or None
        limit = int(args.get("limit", self.config.max_list_items))
        tasks = self.memory.list_tasks(status=status, keyword=keyword, limit=limit)
        if not tasks:
            return ExecutionResult(success=True, message="No matching tasks.", data={"tasks": []})

        lines = [f"{len(tasks)} task(s):"]
        for task in tasks:
            lines.append(self._format_task_line(task))
        return ExecutionResult(success=True, message="\n".join(lines), data={"tasks": [task.id for task in tasks]})

    def complete_task(self, args: dict) -> ExecutionResult:
        task_id = self._parse_task_id(args.get("task_id"))
        if task_id is None:
            return ExecutionResult(success=False, message="Please provide a valid task ID.")
        ok = self.memory.complete_task(task_id)
        if not ok:
            return ExecutionResult(success=False, message=f"Task {task_id} was not found or already completed.")
        task = self.memory.get_task(task_id)
        title = task.title if task else f"#{task_id}"
        return ExecutionResult(success=True, message=f"Task completed: {title}")

    def postpone_task(self, args: dict) -> ExecutionResult:
        task_id = self._parse_task_id(args.get("task_id"))
        days = int(args.get("days", 1))
        if task_id is None:
            return ExecutionResult(success=False, message="Please provide a valid task ID.")
        if days <= 0:
            return ExecutionResult(success=False, message="Postpone days must be greater than 0.")
        ok = self.memory.postpone_task(task_id, days)
        if not ok:
            return ExecutionResult(success=False, message=f"Task {task_id} was not found or postpone failed.")
        task = self.memory.get_task(task_id)
        return ExecutionResult(success=True, message=f"Task {task_id} postponed by {days} day(s). New due date: {task.due_date}")

    def add_note(self, args: dict) -> ExecutionResult:
        content = str(args.get("content", "")).strip()
        if not content:
            return ExecutionResult(success=False, message="Add note failed: content is empty.")
        topic = str(args.get("topic", "general")).strip() or "general"
        tags = normalize_tags(args.get("tags"))
        note_id = self.memory.add_note(content=content, topic=topic, tags=tags)
        details = [f"Note saved. ID: {note_id}", f"Topic: {topic}"]
        if tags:
            details.append(f"Tags: {', '.join(tags)}")
        return ExecutionResult(success=True, message="\n".join(details), data={"note_id": note_id})

    def search_notes(self, args: dict) -> ExecutionResult:
        keyword = str(args.get("keyword", "")).strip()
        if not keyword:
            return ExecutionResult(success=False, message="Please provide a search keyword.")
        limit = int(args.get("limit", 10))
        notes = self.memory.search_notes(keyword, limit=limit)
        if not notes:
            return ExecutionResult(success=True, message=f'No notes found for keyword "{keyword}".')
        lines = [f"{len(notes)} note(s) found:"]
        for note in notes:
            lines.append(self._format_note_line(note))
        return ExecutionResult(success=True, message="\n".join(lines), data={"notes": [note.id for note in notes]})

    def daily_plan(self, args: dict) -> ExecutionResult:
        available_hours = safe_float(args.get("available_hours"))
        if available_hours is None or available_hours <= 0:
            available_hours = self.config.default_daily_hours

        tasks = self.memory.list_tasks(status=TaskStatus.TODO, limit=200)
        if not tasks:
            return ExecutionResult(success=True, message="No TODO tasks right now. You can use time for learning or review.")

        ranked = sorted(tasks, key=self._task_score, reverse=True)
        selected: list[Task] = []
        used = 0.0
        for task in ranked:
            estimate = task.estimate_hours if task.estimate_hours is not None else 1.0
            if used + estimate <= available_hours or not selected:
                selected.append(task)
                used += estimate
            if used >= available_hours:
                break

        lines = [f"Daily plan (available {available_hours:.1f}h):"]
        cursor = 0.0
        for idx, task in enumerate(selected, start=1):
            estimate = task.estimate_hours if task.estimate_hours is not None else 1.0
            start = cursor
            end = cursor + estimate
            cursor = end
            due_label = f" | due {task.due_date}" if task.due_date else ""
            lines.append(
                f"{idx}. {task.title} [{task.priority.value}] | {estimate:.1f}h | slot {start:.1f}-{end:.1f}h{due_label}"
            )

        remaining = max(0.0, available_hours - used)
        lines.append(f"Planned: {used:.1f}h, buffer: {remaining:.1f}h")
        lines.append("Tip: finish the top priorities first, then use buffer time for interruptions.")
        return ExecutionResult(success=True, message="\n".join(lines), data={"selected_task_ids": [t.id for t in selected]})

    def weekly_review(self, _: dict) -> ExecutionResult:
        overview = self.memory.get_overview()
        completed = self.memory.fetch_completed_tasks_since(days=7, limit=8)
        lines = [
            "Weekly review:",
            f"- Total tasks: {overview.total}",
            f"- TODO: {overview.todo}",
            f"- Done: {overview.done}",
            f"- Overdue: {overview.overdue}",
            f"- Completed in last 7 days: {overview.completed_last_7_days}",
            f"- Notes in last 7 days: {overview.notes_last_7_days}",
        ]
        if completed:
            lines.append("- Recently completed:")
            for item in completed[:5]:
                completed_time = item.completed_at or "unknown"
                lines.append(f"  {item.id}. {item.title} ({completed_time})")

        advice: list[str] = []
        if overview.overdue > 0:
            advice.append("Address overdue tasks first and split them into smaller steps if needed.")
        if overview.todo > 10:
            advice.append("Too many TODOs. Consider pruning low-value tasks and re-prioritize.")
        if overview.notes_last_7_days < 3:
            advice.append("Capture more notes. A 3-minute daily log helps with weekly review.")
        if not advice:
            advice.append("Good momentum. Keep your daily plan and weekly review cadence.")

        lines.append("- Next week suggestions:")
        for idx, item in enumerate(advice, start=1):
            lines.append(f"  {idx}. {item}")
        return ExecutionResult(success=True, message="\n".join(lines))

    def show_help(self, args: dict) -> ExecutionResult:
        hint = str(args.get("hint", "")).strip()
        lines = [
            "Example commands:",
            "1. add task Write weekly report --priority high --due tomorrow --estimate 2 --tags work,output",
            "2. list tasks",
            "3. complete task 3",
            "4. postpone task 3 2",
            "5. add note Discussed quarterly goals --topic meeting --tags strategy,team",
            "6. search notes quarterly",
            "7. daily plan 6 hours",
            "8. weekly review",
            "9. help",
            "10. exit",
        ]
        if hint:
            lines.insert(0, f"I could not fully understand your input: {hint}")
        return ExecutionResult(success=True, message="\n".join(lines))

    def exit_agent(self, _: dict) -> ExecutionResult:
        return ExecutionResult(success=True, message="Session ended. See you next time.", data={"exit": True})

    def _format_task_line(self, task: Task) -> str:
        due = f" | due: {task.due_date}" if task.due_date else ""
        estimate = f" | est: {task.estimate_hours:.1f}h" if task.estimate_hours is not None else ""
        tags = f" | tags: {', '.join(task.tags)}" if task.tags else ""
        return f"[{task.id}] [{task.priority.value}] {task.status.value.upper()} {task.title}{due}{estimate}{tags}"

    @staticmethod
    def _format_note_line(note: Note) -> str:
        snippet = note.content if len(note.content) <= 60 else f"{note.content[:57]}..."
        tags = f" | tags: {', '.join(note.tags)}" if note.tags else ""
        return f"[{note.id}] topic: {note.topic} | time: {note.created_at} | content: {snippet}{tags}"

    @staticmethod
    def _parse_task_id(raw: object) -> int | None:
        try:
            if raw is None:
                return None
            return int(str(raw).strip())
        except ValueError:
            return None

    @staticmethod
    def _task_score(task: Task) -> float:
        priority_weight = {
            Priority.URGENT: 10.0,
            Priority.HIGH: 7.0,
            Priority.MEDIUM: 4.0,
            Priority.LOW: 2.0,
        }
        score = priority_weight.get(task.priority, 4.0)
        if task.due_date:
            try:
                days_left = (date.fromisoformat(task.due_date) - date.today()).days
            except ValueError:
                days_left = 7
            if days_left < 0:
                score += 10.0
            elif days_left == 0:
                score += 7.0
            elif days_left <= 2:
                score += 4.0
        if task.estimate_hours is not None and task.estimate_hours <= 1.0:
            score += 0.5
        return score


def build_default_registry(memory: SQLiteMemoryStore, config: AgentConfig) -> ToolRegistry:
    registry = ToolRegistry()
    toolset = AgentTools(memory=memory, config=config)
    registry.register(Tool("create_task", "create task", toolset.create_task))
    registry.register(Tool("list_tasks", "list tasks", toolset.list_tasks))
    registry.register(Tool("complete_task", "complete task", toolset.complete_task))
    registry.register(Tool("postpone_task", "postpone task", toolset.postpone_task))
    registry.register(Tool("add_note", "add note", toolset.add_note))
    registry.register(Tool("search_notes", "search notes", toolset.search_notes))
    registry.register(Tool("daily_plan", "build daily plan", toolset.daily_plan))
    registry.register(Tool("weekly_review", "build weekly review", toolset.weekly_review))
    registry.register(Tool("show_help", "show help", toolset.show_help))
    registry.register(Tool("exit_agent", "exit", toolset.exit_agent))
    return registry

