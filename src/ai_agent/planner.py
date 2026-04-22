from __future__ import annotations

import re
import shlex

from .models import IntentType, ParsedIntent, PlanStep
from .utils import parse_natural_date


CN_EXIT = "\u9000\u51fa"
CN_END = "\u7ed3\u675f"
CN_HELP = "\u5e2e\u52a9"
CN_COMPLETE_TASK = "\u5b8c\u6210\u4efb\u52a1"
CN_POSTPONE_TASK = "\u5ef6\u671f\u4efb\u52a1"
CN_POSTPONE_TASK_2 = "\u5ef6\u540e\u4efb\u52a1"
CN_LIST_TASKS = "\u5217\u51fa\u4efb\u52a1"
CN_TASK_LIST = "\u4efb\u52a1\u5217\u8868"
CN_KEYWORD = "\u5173\u952e\u8bcd"
CN_DAILY_PLAN = "\u4eca\u65e5\u8ba1\u5212"
CN_TODAY_PLAN = "\u4eca\u5929\u8ba1\u5212"
CN_WEEKLY_REVIEW = "\u5468\u590d\u76d8"
CN_WEEKLY_REVIEW_2 = "\u672c\u5468\u590d\u76d8"
CN_WEEKLY_SUMMARY = "\u5468\u603b\u7ed3"
CN_SEARCH_NOTES = "\u641c\u7d22\u7b14\u8bb0"
CN_FIND_NOTES = "\u67e5\u627e\u7b14\u8bb0"
CN_ADD_NOTE = "\u8bb0\u7b14\u8bb0"
CN_ADD_NOTE_2 = "\u6dfb\u52a0\u7b14\u8bb0"
CN_ADD_TASK = "\u6dfb\u52a0\u4efb\u52a1"
CN_CREATE_TASK = "\u521b\u5efa\u4efb\u52a1"
CN_NEW_TASK = "\u65b0\u589e\u4efb\u52a1"
CN_DESC = "\u63cf\u8ff0"
CN_PRIORITY = "\u4f18\u5148\u7ea7"
CN_DUE = "\u622a\u6b62"
CN_ESTIMATE = "\u9884\u4f30"
CN_TAGS = "\u6807\u7b7e"


class IntentParser:
    def parse(self, message: str) -> ParsedIntent:
        text = message.strip()
        lowered = text.lower()
        if not text:
            return ParsedIntent(IntentType.HELP, confidence=1.0, raw_text=message)

        if lowered in {"exit", "quit", "bye", CN_EXIT, CN_END}:
            return ParsedIntent(IntentType.EXIT, confidence=1.0, raw_text=message)

        if lowered in {"help", CN_HELP, "h", "?"}:
            return ParsedIntent(IntentType.HELP, confidence=1.0, raw_text=message)

        complete_match = re.search(
            rf"(?:{CN_COMPLETE_TASK}|done|complete task|mark done)\s*#?\s*(\d+)",
            lowered,
        )
        if complete_match:
            return ParsedIntent(
                IntentType.COMPLETE_TASK,
                args={"task_id": int(complete_match.group(1))},
                confidence=0.95,
                raw_text=message,
            )

        postpone_match = re.search(
            rf"(?:{CN_POSTPONE_TASK}|{CN_POSTPONE_TASK_2}|postpone task|postpone)\s*#?\s*(\d+)(?:\s+(\d+))?",
            lowered,
        )
        if postpone_match:
            days = int(postpone_match.group(2)) if postpone_match.group(2) else 1
            return ParsedIntent(
                IntentType.POSTPONE_TASK,
                args={"task_id": int(postpone_match.group(1)), "days": days},
                confidence=0.92,
                raw_text=message,
            )

        if self._is_list_tasks(text, lowered):
            args: dict[str, object] = {}
            if "\u5df2\u5b8c\u6210" in text or "done" in lowered:
                args["status"] = "done"
            elif "\u5f85\u529e" in text or "todo" in lowered:
                args["status"] = "todo"
            keyword_match = re.search(rf"(?:{CN_KEYWORD}|keyword)\s*[=:]\s*([^\s]+)", text)
            if keyword_match:
                args["keyword"] = keyword_match.group(1)
            return ParsedIntent(IntentType.LIST_TASKS, args=args, confidence=0.88, raw_text=message)

        if self._is_daily_plan(text, lowered):
            hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\u5c0f\u65f6|h|hours?)", lowered)
            args: dict[str, object] = {}
            if hour_match:
                args["available_hours"] = float(hour_match.group(1))
            return ParsedIntent(IntentType.DAILY_PLAN, args=args, confidence=0.9, raw_text=message)

        if self._is_weekly_review(text, lowered):
            return ParsedIntent(IntentType.WEEKLY_REVIEW, confidence=0.9, raw_text=message)

        note_search_match = re.search(
            rf"(?:{CN_SEARCH_NOTES}|{CN_FIND_NOTES}|search notes?)\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if note_search_match:
            keyword = note_search_match.group(1).strip()
            return ParsedIntent(IntentType.SEARCH_NOTES, args={"keyword": keyword}, confidence=0.9, raw_text=message)

        note_match = re.match(rf"(?:{CN_ADD_NOTE}|{CN_ADD_NOTE_2}|note|add note)\s+(.+)", text, flags=re.IGNORECASE)
        if note_match:
            payload = note_match.group(1).strip()
            content, options = self._extract_options(payload)
            args = {
                "content": content,
                "topic": options.get("topic") or options.get("\u4e3b\u9898") or "general",
                "tags": options.get("tags") or options.get(CN_TAGS),
            }
            return ParsedIntent(IntentType.ADD_NOTE, args=args, confidence=0.93, raw_text=message)

        create_match = re.match(
            rf"(?:{CN_ADD_TASK}|{CN_NEW_TASK}|{CN_CREATE_TASK}|add task|create task)\s+(.+)",
            text,
            flags=re.IGNORECASE,
        )
        if create_match:
            payload = create_match.group(1).strip()
            title, options = self._extract_options(payload)
            due = options.get("due") or options.get(CN_DUE)
            due_date = parse_natural_date(str(due)) if due else None
            args = {
                "title": title,
                "description": options.get("desc") or options.get("description") or options.get(CN_DESC) or "",
                "priority": options.get("priority") or options.get(CN_PRIORITY) or "medium",
                "due_date": due_date or due,
                "estimate_hours": options.get("estimate") or options.get(CN_ESTIMATE),
                "tags": options.get("tags") or options.get(CN_TAGS),
            }
            return ParsedIntent(IntentType.CREATE_TASK, args=args, confidence=0.95, raw_text=message)

        if ("\u4efb\u52a1" in text and ("\u521b\u5efa" in text or "\u65b0\u589e" in text or "\u6dfb\u52a0" in text)) or lowered.startswith(
            "task "
        ):
            return ParsedIntent(IntentType.CREATE_TASK, args={"title": text}, confidence=0.55, raw_text=message)

        return ParsedIntent(IntentType.UNKNOWN, confidence=0.2, raw_text=message)

    @staticmethod
    def _is_list_tasks(text: str, lowered: str) -> bool:
        hard_keys = {
            CN_LIST_TASKS,
            CN_TASK_LIST,
            "list tasks",
            "list task",
        }
        if lowered in hard_keys:
            return True
        fuzzy_keys = (
            CN_LIST_TASKS,
            CN_TASK_LIST,
            "\u770b\u4efb\u52a1",
            "\u770b\u770b\u4efb\u52a1",
            "\u6211\u7684\u4efb\u52a1",
            "\u6709\u54ea\u4e9b\u4efb\u52a1",
            "todo",
            "list tasks",
        )
        return any(key in lowered or key in text for key in fuzzy_keys)

    @staticmethod
    def _is_daily_plan(text: str, lowered: str) -> bool:
        keys = (CN_DAILY_PLAN, CN_TODAY_PLAN, "\u5e2e\u6211\u5b89\u6392\u4eca\u5929", "daily plan", "day plan")
        return any(item in lowered or item in text for item in keys)

    @staticmethod
    def _is_weekly_review(text: str, lowered: str) -> bool:
        keys = (CN_WEEKLY_REVIEW, CN_WEEKLY_REVIEW_2, "weekly review", "week review", CN_WEEKLY_SUMMARY)
        return any(item in lowered or item in text for item in keys)

    @staticmethod
    def _extract_options(payload: str) -> tuple[str, dict[str, str]]:
        options: dict[str, str] = {}
        title_parts: list[str] = []

        try:
            tokens = shlex.split(payload)
        except ValueError:
            tokens = payload.split()

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--"):
                key = token[2:].strip().lower()
                value = "true"
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    values: list[str] = []
                    j = i + 1
                    while j < len(tokens) and not tokens[j].startswith("--"):
                        values.append(tokens[j])
                        j += 1
                    value = " ".join(values).strip()
                    i = j - 1
                options[key] = value
            elif "=" in token:
                key, value = token.split("=", 1)
                options[key.strip()] = value.strip()
            elif "\uff1a" in token:
                key, value = token.split("\uff1a", 1)
                options[key.strip()] = value.strip()
            else:
                title_parts.append(token)
            i += 1
        title = " ".join(title_parts).strip()
        return title, options


class OfflinePlanningBrain:
    def create_plan(self, intent: ParsedIntent) -> list[PlanStep]:
        mapping = {
            IntentType.CREATE_TASK: "create_task",
            IntentType.LIST_TASKS: "list_tasks",
            IntentType.COMPLETE_TASK: "complete_task",
            IntentType.POSTPONE_TASK: "postpone_task",
            IntentType.ADD_NOTE: "add_note",
            IntentType.SEARCH_NOTES: "search_notes",
            IntentType.DAILY_PLAN: "daily_plan",
            IntentType.WEEKLY_REVIEW: "weekly_review",
            IntentType.HELP: "show_help",
            IntentType.EXIT: "exit_agent",
            IntentType.UNKNOWN: "show_help",
        }
        tool_name = mapping[intent.intent]
        args = dict(intent.args)
        if intent.intent is IntentType.UNKNOWN:
            args["hint"] = intent.raw_text
        return [PlanStep(tool_name=tool_name, args=args)]

