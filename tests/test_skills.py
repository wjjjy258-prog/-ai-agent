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


class SkillFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "agent.db"
        os.environ["AURORA_ENABLE_LLM_CHAT"] = "false"
        self.config = AgentConfig.from_db_path(db_path)
        self.agent = AIAgent(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("AURORA_ENABLE_LLM_CHAT", None)

    def test_default_skills_and_matching(self) -> None:
        defaults = self.agent.memory.list_skills(limit=20)
        self.assertGreaterEqual(len(defaults), 3)

        created = self.agent.memory.create_skill(
            name="接口调试",
            description="定位接口层问题",
            instruction="当用户提到接口排查时，优先列调用链和异常点。",
            trigger_keywords=["接口调试", "接口排查"],
            enabled=True,
        )
        matches = self.agent.memory.match_skills("请帮我做接口调试", limit=10)
        self.assertIn(created.id, [item.id for item in matches])

    def test_selected_model_persists_across_agent_reloads(self) -> None:
        self.agent.select_model("llama3.1:8b")
        reloaded = AIAgent(AgentConfig.from_db_path(self.config.db_path))
        self.assertEqual(reloaded.runtime_metadata["model"], "llama3.1:8b")


if __name__ == "__main__":
    unittest.main()
