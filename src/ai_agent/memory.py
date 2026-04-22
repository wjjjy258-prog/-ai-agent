from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .models import ChatMessage, Conversation, Note, Priority, Skill, Task, TaskStatus


@dataclass(slots=True)
class TaskOverview:
    total: int
    todo: int
    done: int
    overdue: int
    completed_last_7_days: int
    notes_last_7_days: int


DEFAULT_CONVERSATION_TITLE = "新对话"
DEFAULT_SKILLS: tuple[dict[str, object], ...] = (
    {
        "name": "代码审阅",
        "description": "当用户要求 review、排查风险或检查代码时，先列问题，再补建议。",
        "instruction": (
            "优先发现 bug、回归风险、边界条件和缺失测试。"
            "先给问题列表，再给简短总结；不要把夸奖放在前面。"
        ),
        "trigger_keywords": ["review", "代码审查", "审查代码", "检查代码", "风险排查"],
    },
    {
        "name": "学习教练",
        "description": "当用户想学原理时，用循序渐进的方式解释，并给出例子。",
        "instruction": (
            "按“先整体、再细节、最后例子”的顺序解释。"
            "尽量说明为什么这样设计，而不只是它是什么。"
        ),
        "trigger_keywords": ["原理", "学习", "教我", "讲解", "解释一下"],
    },
    {
        "name": "写作优化",
        "description": "当用户需要润色、改写、整理表达时，优先输出更清晰、自然的中文。",
        "instruction": (
            "保留原意，优化结构、节奏和可读性。"
            "如果适合，给出一个更简洁版本和一个更正式版本。"
        ),
        "trigger_keywords": ["润色", "改写", "重写", "总结", "优化文案"],
    },
)


class SQLiteMemoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()
        self._seed_default_skills()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _create_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'todo',
                    due_date TEXT,
                    estimate_hours REAL,
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    topic TEXT NOT NULL DEFAULT 'general',
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    instruction TEXT NOT NULL,
                    trigger_keywords TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
                ON conversations(updated_at DESC);

                CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id
                ON conversation_messages(conversation_id, id);

                CREATE INDEX IF NOT EXISTS idx_skills_enabled_updated_at
                ON skills(enabled, updated_at DESC);
                """
            )

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _utc_now_iso(cls) -> str:
        return cls._utc_now().isoformat(timespec="seconds")

    @staticmethod
    def _serialize_tags(tags: list[str]) -> str:
        return ",".join(tag.strip() for tag in tags if tag.strip())

    @staticmethod
    def _deserialize_tags(raw: str) -> list[str]:
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    def _seed_default_skills(self) -> None:
        with self._connect() as conn:
            existing = int(conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0])
            if existing > 0:
                return
            now = self._utc_now_iso()
            for item in DEFAULT_SKILLS:
                conn.execute(
                    """
                    INSERT INTO skills (id, name, description, instruction, trigger_keywords, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        uuid4().hex,
                        str(item["name"]),
                        str(item["description"]),
                        str(item["instruction"]),
                        self._serialize_tags(list(item["trigger_keywords"])),
                        now,
                        now,
                    ),
                )

    def add_task(
        self,
        *,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
        estimate_hours: float | None = None,
        tags: list[str] | None = None,
    ) -> int:
        tags = tags or []
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (title, description, priority, status, due_date, estimate_hours, tags, created_at, updated_at)
                VALUES (?, ?, ?, 'todo', ?, ?, ?, ?, ?)
                """,
                (title, description, priority.value, due_date, estimate_hours, self._serialize_tags(tags), now, now),
            )
            return int(cursor.lastrowid)

    def list_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> list[Task]:
        conditions: list[str] = []
        params: list[object] = []

        if status is not None:
            conditions.append("status = ?")
            params.append(status.value)
        if keyword:
            conditions.append("(title LIKE ? OR description LIKE ? OR tags LIKE ?)")
            like = f"%{keyword.strip()}%"
            params.extend([like, like, like])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        query = f"""
            SELECT *
            FROM tasks
            {where_clause}
            ORDER BY
                CASE status WHEN 'todo' THEN 0 ELSE 1 END ASC,
                CASE priority
                    WHEN 'urgent' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END ASC,
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,
                due_date ASC,
                updated_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Task | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def complete_task(self, task_id: int) -> bool:
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE tasks
                SET status = 'done', completed_at = ?, updated_at = ?
                WHERE id = ? AND status != 'done'
                """,
                (now, now, task_id),
            )
            return cursor.rowcount > 0

    def postpone_task(self, task_id: int, days: int) -> bool:
        if days <= 0:
            return False
        task = self.get_task(task_id)
        if task is None:
            return False

        base_date = self._utc_now().date()
        if task.due_date:
            try:
                base_date = datetime.fromisoformat(task.due_date).date()
            except ValueError:
                pass
        next_date = (base_date + timedelta(days=days)).isoformat()
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET due_date = ?, updated_at = ? WHERE id = ?",
                (next_date, now, task_id),
            )
            return cursor.rowcount > 0

    def add_note(self, *, content: str, topic: str = "general", tags: list[str] | None = None) -> int:
        tags = tags or []
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO notes (content, topic, tags, created_at) VALUES (?, ?, ?, ?)",
                (content, topic, self._serialize_tags(tags), now),
            )
            return int(cursor.lastrowid)

    def search_notes(self, keyword: str, *, limit: int = 10) -> list[Note]:
        like = f"%{keyword.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM notes
                WHERE content LIKE ? OR topic LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (like, like, like, limit),
            ).fetchall()
        return [self._row_to_note(row) for row in rows]

    def record_interaction(self, role: str, content: str) -> None:
        now = self._utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO interactions (role, content, created_at) VALUES (?, ?, ?)",
                (role, content, now),
            )

    def get_recent_interactions(self, *, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM interactions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in rows[::-1]
        ]

    def create_conversation(self, title: str | None = None) -> Conversation:
        conversation_id = uuid4().hex
        now = self._utc_now_iso()
        normalized_title = self._normalize_conversation_title(title)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, normalized_title, now, now),
            )
        return Conversation(
            id=conversation_id,
            title=normalized_title,
            created_at=now,
            updated_at=now,
            last_message_preview="",
            message_count=0,
        )

    def list_conversations(self, *, limit: int = 100) -> list[Conversation]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    COALESCE((
                        SELECT cm.content
                        FROM conversation_messages cm
                        WHERE cm.conversation_id = c.id
                        ORDER BY cm.id DESC
                        LIMIT 1
                    ), '') AS last_message_preview,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM conversation_messages cm2
                        WHERE cm2.conversation_id = c.id
                    ), 0) AS message_count
                FROM conversations c
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_conversation(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    COALESCE((
                        SELECT cm.content
                        FROM conversation_messages cm
                        WHERE cm.conversation_id = c.id
                        ORDER BY cm.id DESC
                        LIMIT 1
                    ), '') AS last_message_preview,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM conversation_messages cm2
                        WHERE cm2.conversation_id = c.id
                    ), 0) AS message_count
                FROM conversations c
                WHERE c.id = ?
                """,
                (conversation_id,),
            ).fetchone()
        return self._row_to_conversation(row) if row else None

    def rename_conversation(self, conversation_id: str, title: str) -> bool:
        normalized_title = self._normalize_conversation_title(title)
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (normalized_title, now, conversation_id),
            )
            return cursor.rowcount > 0

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            return cursor.rowcount > 0

    def add_conversation_message(self, *, conversation_id: str, role: str, content: str) -> int:
        now = self._utc_now_iso()
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM conversations WHERE id = ? LIMIT 1",
                (conversation_id,),
            ).fetchone()
            if exists is None:
                raise ValueError(f"Conversation not found: {conversation_id}")

            cursor = conn.execute(
                """
                INSERT INTO conversation_messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            message_id = int(cursor.lastrowid)

            if role == "user":
                row = conn.execute(
                    "SELECT title FROM conversations WHERE id = ?",
                    (conversation_id,),
                ).fetchone()
                if row and row["title"] == DEFAULT_CONVERSATION_TITLE:
                    first_user = conn.execute(
                        """
                        SELECT content
                        FROM conversation_messages
                        WHERE conversation_id = ? AND role = 'user'
                        ORDER BY id ASC
                        LIMIT 1
                        """,
                        (conversation_id,),
                    ).fetchone()
                    if first_user:
                        conn.execute(
                            "UPDATE conversations SET title = ? WHERE id = ?",
                            (self._normalize_conversation_title(first_user["content"]), conversation_id),
                        )

            return message_id

    def list_conversation_messages(self, conversation_id: str, *, limit: int = 200) -> list[ChatMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, created_at
                FROM (
                    SELECT *
                    FROM conversation_messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (conversation_id, limit),
            ).fetchall()
        return [self._row_to_chat_message(row) for row in rows]

    def get_setting(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        now = self._utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )

    def list_skills(self, *, enabled_only: bool | None = None, limit: int = 200) -> list[Skill]:
        conditions: list[str] = []
        params: list[object] = []
        if enabled_only is True:
            conditions.append("enabled = 1")
        elif enabled_only is False:
            conditions.append("enabled = 0")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        query = f"""
            SELECT *
            FROM skills
            {where_clause}
            ORDER BY enabled DESC, updated_at DESC, name COLLATE NOCASE ASC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_skill(row) for row in rows]

    def get_skill(self, skill_id: str) -> Skill | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        return self._row_to_skill(row) if row else None

    def create_skill(
        self,
        *,
        name: str,
        description: str,
        instruction: str,
        trigger_keywords: list[str] | None = None,
        enabled: bool = True,
    ) -> Skill:
        skill_id = uuid4().hex
        now = self._utc_now_iso()
        keywords = self._serialize_tags(trigger_keywords or [])
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO skills (id, name, description, instruction, trigger_keywords, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (skill_id, name.strip(), description.strip(), instruction.strip(), keywords, int(enabled), now, now),
            )
        skill = self.get_skill(skill_id)
        if skill is None:
            raise RuntimeError("Skill saved but could not be loaded.")
        return skill

    def update_skill(
        self,
        skill_id: str,
        *,
        name: str,
        description: str,
        instruction: str,
        trigger_keywords: list[str] | None = None,
        enabled: bool,
    ) -> Skill | None:
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE skills
                SET name = ?, description = ?, instruction = ?, trigger_keywords = ?, enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    description.strip(),
                    instruction.strip(),
                    self._serialize_tags(trigger_keywords or []),
                    int(enabled),
                    now,
                    skill_id,
                ),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_skill(skill_id)

    def set_skill_enabled(self, skill_id: str, enabled: bool) -> Skill | None:
        now = self._utc_now_iso()
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE skills SET enabled = ?, updated_at = ? WHERE id = ?",
                (int(enabled), now, skill_id),
            )
            if cursor.rowcount <= 0:
                return None
        return self.get_skill(skill_id)

    def delete_skill(self, skill_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
            return cursor.rowcount > 0

    def match_skills(self, message: str, *, limit: int = 4) -> list[Skill]:
        normalized = message.strip().lower()
        if not normalized:
            return []

        matched: list[Skill] = []
        always_on: list[Skill] = []
        for skill in self.list_skills(enabled_only=True, limit=200):
            keywords = [item.lower() for item in skill.trigger_keywords if item.strip()]
            if not keywords:
                always_on.append(skill)
                continue
            if any(keyword in normalized for keyword in keywords):
                matched.append(skill)

        combined = always_on + matched
        deduped: list[Skill] = []
        seen: set[str] = set()
        for skill in combined:
            if skill.id in seen:
                continue
            deduped.append(skill)
            seen.add(skill.id)
            if len(deduped) >= limit:
                break
        return deduped

    def _normalize_conversation_title(self, raw: str | None) -> str:
        if not raw:
            return DEFAULT_CONVERSATION_TITLE
        cleaned = " ".join(raw.strip().split())
        if not cleaned:
            return DEFAULT_CONVERSATION_TITLE
        return cleaned[:48]

    def fetch_completed_tasks_since(self, *, days: int = 7, limit: int = 20) -> list[Task]:
        start = (self._utc_now() - timedelta(days=days)).isoformat(timespec="seconds")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM tasks
                WHERE status = 'done' AND completed_at >= ?
                ORDER BY completed_at DESC
                LIMIT ?
                """,
                (start, limit),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_overview(self) -> TaskOverview:
        today = self._utc_now().date().isoformat()
        start = (self._utc_now() - timedelta(days=7)).isoformat(timespec="seconds")
        with self._connect() as conn:
            total = int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
            todo = int(conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'todo'").fetchone()[0])
            done = int(conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'").fetchone()[0])
            overdue = int(
                conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = 'todo' AND due_date IS NOT NULL AND due_date < ?",
                    (today,),
                ).fetchone()[0]
            )
            completed_last_7_days = int(
                conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = 'done' AND completed_at >= ?",
                    (start,),
                ).fetchone()[0]
            )
            notes_last_7_days = int(
                conn.execute("SELECT COUNT(*) FROM notes WHERE created_at >= ?", (start,)).fetchone()[0]
            )
        return TaskOverview(
            total=total,
            todo=todo,
            done=done,
            overdue=overdue,
            completed_last_7_days=completed_last_7_days,
            notes_last_7_days=notes_last_7_days,
        )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=int(row["id"]),
            title=row["title"],
            description=row["description"],
            priority=Priority(row["priority"]),
            status=TaskStatus(row["status"]),
            due_date=row["due_date"],
            estimate_hours=float(row["estimate_hours"]) if row["estimate_hours"] is not None else None,
            tags=self._deserialize_tags(row["tags"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    def _row_to_note(self, row: sqlite3.Row) -> Note:
        return Note(
            id=int(row["id"]),
            content=row["content"],
            topic=row["topic"],
            tags=self._deserialize_tags(row["tags"]),
            created_at=row["created_at"],
        )

    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        preview = row["last_message_preview"] or ""
        if len(preview) > 90:
            preview = f"{preview[:87]}..."
        return Conversation(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_message_preview=preview,
            message_count=int(row["message_count"]),
        )

    def _row_to_chat_message(self, row: sqlite3.Row) -> ChatMessage:
        return ChatMessage(
            id=int(row["id"]),
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
        )

    def _row_to_skill(self, row: sqlite3.Row) -> Skill:
        return Skill(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            instruction=row["instruction"],
            trigger_keywords=self._deserialize_tags(row["trigger_keywords"]),
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
