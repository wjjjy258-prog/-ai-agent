import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent.llm import OllamaLLMClient


class OllamaCacheTests(unittest.TestCase):
    def test_remote_model_list_is_cached(self) -> None:
        client = OllamaLLMClient(base_url="http://127.0.0.1:11434", model="qwen3.5:4b")
        calls = {"count": 0}

        def fake_fetch(url: str) -> str:
            calls["count"] += 1
            if "q=qwen" not in url:
                return "<ul></ul>"
            return """
<ul>
  <li x-test-model>
    <a href="/library/qwen3.5"></a>
    <span x-test-search-response-title>Qwen3.5</span>
    <p class="max-w-lg">Qwen model</p>
  </li>
</ul>
"""

        client._fetch_text = fake_fetch  # type: ignore[method-assign]
        first = client.list_remote_models(query="qwen", page=1)
        second = client.list_remote_models(query="qwen", page=1)
        third = client.list_remote_models(query="llama", page=1)

        self.assertEqual(calls["count"], 2)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(third, [])

    def test_model_tags_are_cached(self) -> None:
        client = OllamaLLMClient(base_url="http://127.0.0.1:11434", model="qwen3.5:4b")
        calls = {"count": 0}

        def fake_fetch(url: str) -> str:
            calls["count"] += 1
            if "llama3.1" in url:
                return "<div></div>"
            return """
<div>
  <a href="/library/qwen3.5:latest"></a>
  <a href="/library/qwen3.5:8b"></a>
</div>
"""

        client._fetch_text = fake_fetch  # type: ignore[method-assign]
        first = client.list_model_tags("qwen3.5")
        second = client.list_model_tags("qwen3.5")
        other = client.list_model_tags("llama3.1")

        self.assertEqual(calls["count"], 2)
        self.assertEqual(len(first), 2)
        self.assertEqual(first, second)
        self.assertEqual(other, [])


if __name__ == "__main__":
    unittest.main()
