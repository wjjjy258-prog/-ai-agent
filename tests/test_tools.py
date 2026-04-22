import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent.config import AgentConfig
from ai_agent.memory import SQLiteMemoryStore
from ai_agent.tools import build_default_registry


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "agent.db"
        os.environ["AURORA_ENABLE_LLM_CHAT"] = "false"
        self.config = AgentConfig.from_db_path(db_path)
        self.memory = SQLiteMemoryStore(self.config.db_path)
        self.registry = build_default_registry(self.memory, self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("AURORA_ENABLE_LLM_CHAT", None)

    def test_task_lifecycle(self) -> None:
        created = self.registry.execute(
            "create_task",
            {
                "title": "Implement login page",
                "priority": "high",
                "estimate_hours": "3",
                "due_date": "tomorrow",
                "tags": "frontend,projectA",
            },
        )
        self.assertTrue(created.success)
        task_id = created.data["task_id"]

        listed = self.registry.execute("list_tasks", {})
        self.assertTrue(listed.success)
        self.assertIn("Implement login page", listed.message)

        done = self.registry.execute("complete_task", {"task_id": task_id})
        self.assertTrue(done.success)

        listed_done = self.registry.execute("list_tasks", {"status": "done"})
        self.assertIn("DONE", listed_done.message)

    def test_note_search(self) -> None:
        add = self.registry.execute(
            "add_note",
            {
                "content": "Release strategy confirmed: canary first, then full rollout.",
                "topic": "release",
                "tags": "strategy,meeting",
            },
        )
        self.assertTrue(add.success)

        search = self.registry.execute("search_notes", {"keyword": "canary"})
        self.assertTrue(search.success)
        self.assertIn("release", search.message)

    def test_daily_plan(self) -> None:
        self.registry.execute("create_task", {"title": "Task A", "priority": "urgent", "estimate_hours": 2})
        self.registry.execute("create_task", {"title": "Task B", "priority": "medium", "estimate_hours": 1})
        plan = self.registry.execute("daily_plan", {"available_hours": 2.5})
        self.assertTrue(plan.success)
        self.assertIn("Daily plan", plan.message)
        self.assertIn("Task A", plan.message)


if __name__ == "__main__":
    unittest.main()
