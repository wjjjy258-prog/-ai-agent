import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent.models import IntentType
from ai_agent.planner import IntentParser


class IntentParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = IntentParser()

    def test_parse_create_task_with_flags(self) -> None:
        parsed = self.parser.parse(
            "add task Write quarterly report --priority high --due tomorrow --estimate 2 --tags work,report --desc align Q2 goals"
        )
        self.assertEqual(parsed.intent, IntentType.CREATE_TASK)
        self.assertEqual(parsed.args["title"], "Write quarterly report")
        self.assertEqual(parsed.args["priority"], "high")
        self.assertEqual(parsed.args["estimate_hours"], "2")
        self.assertEqual(parsed.args["tags"], "work,report")
        self.assertEqual(parsed.args["description"], "align Q2 goals")
        self.assertIsNotNone(parsed.args["due_date"])

    def test_parse_complete_task(self) -> None:
        parsed = self.parser.parse("complete task 18")
        self.assertEqual(parsed.intent, IntentType.COMPLETE_TASK)
        self.assertEqual(parsed.args["task_id"], 18)

    def test_parse_daily_plan(self) -> None:
        parsed = self.parser.parse("daily plan 5 hours")
        self.assertEqual(parsed.intent, IntentType.DAILY_PLAN)
        self.assertAlmostEqual(parsed.args["available_hours"], 5.0)

    def test_unknown_input(self) -> None:
        parsed = self.parser.parse("This sentence does not contain command keywords")
        self.assertEqual(parsed.intent, IntentType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()

