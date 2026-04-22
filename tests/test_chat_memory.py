import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent.memory import SQLiteMemoryStore


class ChatMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "agent.db"
        self.store = SQLiteMemoryStore(db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_conversation_lifecycle(self) -> None:
        conversation = self.store.create_conversation("Sprint Planning")
        self.assertEqual(conversation.title, "Sprint Planning")

        self.store.add_conversation_message(
            conversation_id=conversation.id,
            role="user",
            content="Please build the release checklist.",
        )
        self.store.add_conversation_message(
            conversation_id=conversation.id,
            role="assistant",
            content="Sure. I can produce a checklist by owner and deadline.",
        )

        fetched = self.store.get_conversation(conversation.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.message_count, 2)

        messages = self.store.list_conversation_messages(conversation.id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(messages[1].role, "assistant")

        self.assertTrue(self.store.rename_conversation(conversation.id, "Release Plan"))
        renamed = self.store.get_conversation(conversation.id)
        self.assertEqual(renamed.title, "Release Plan")

        self.assertTrue(self.store.delete_conversation(conversation.id))
        self.assertIsNone(self.store.get_conversation(conversation.id))


if __name__ == "__main__":
    unittest.main()

