import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent.agent import AIAgent
from ai_agent.config import AgentConfig


class AgentFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "agent.db"
        os.environ["AURORA_ENABLE_LLM_CHAT"] = "false"
        config = AgentConfig.from_db_path(db_path)
        self.agent = AIAgent(config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("AURORA_ENABLE_LLM_CHAT", None)

    def test_full_flow(self) -> None:
        create_resp = self.agent.handle_message("add task Write API doc --priority high --estimate 2 --due tomorrow")
        self.assertIn("Task created", create_resp)

        list_resp = self.agent.handle_message("list tasks")
        self.assertIn("Write API doc", list_resp)

        plan_resp = self.agent.handle_message("daily plan 2 hours")
        self.assertIn("Daily plan", plan_resp)

    def test_exit(self) -> None:
        resp = self.agent.handle_message("exit")
        self.assertIn("Session ended", resp)
        self.assertTrue(self.agent.should_exit)


if __name__ == "__main__":
    unittest.main()
