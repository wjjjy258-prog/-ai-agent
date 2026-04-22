import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent.web.app import create_app


class WebApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        db_path = self.temp_path / "agent.db"
        os.environ["AURORA_ENABLE_LLM_CHAT"] = "false"
        app = create_app(db_path)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("AURORA_ENABLE_LLM_CHAT", None)

    def test_create_and_chat(self) -> None:
        runtime = self.client.get("/api/runtime")
        self.assertEqual(runtime.status_code, 200)
        self.assertIn("runtime", runtime.json())

        models = self.client.get("/api/models")
        self.assertEqual(models.status_code, 200)
        self.assertIn("items", models.json())

        created = self.client.post("/api/conversations", json={"title": "QA Session"})
        self.assertEqual(created.status_code, 200)
        conversation_id = created.json()["conversation"]["id"]

        sent = self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "help"},
        )
        self.assertEqual(sent.status_code, 200)
        payload = sent.json()
        self.assertEqual(payload["user_message"]["role"], "user")
        self.assertEqual(payload["assistant_message"]["role"], "assistant")
        self.assertTrue(payload["assistant_message"]["content"])

        stream_resp = self.client.post(
            f"/api/conversations/{conversation_id}/messages/stream",
            json={"content": "list tasks"},
        )
        self.assertEqual(stream_resp.status_code, 200)
        stream_body = stream_resp.text.strip().splitlines()
        self.assertTrue(any('"type": "chunk"' in line for line in stream_body))
        self.assertTrue(any('"type": "done"' in line for line in stream_body))

        listed = self.client.get(f"/api/conversations/{conversation_id}/messages")
        self.assertEqual(listed.status_code, 200)
        self.assertGreaterEqual(len(listed.json()["items"]), 4)

    def test_skill_and_model_management_endpoints(self) -> None:
        created = self.client.post(
            "/api/skills",
            json={
                "name": "Meeting Notes",
                "description": "Summarize meeting outcomes",
                "instruction": "Organize output into decisions, todo, and risks.",
                "trigger_keywords": "meeting,summary,notes",
                "enabled": True,
            },
        )
        self.assertEqual(created.status_code, 200)
        skill_id = created.json()["skill"]["id"]

        listed = self.client.get("/api/skills")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(item["id"] == skill_id for item in listed.json()["items"]))

        toggled = self.client.patch(f"/api/skills/{skill_id}/toggle", json={"enabled": False})
        self.assertEqual(toggled.status_code, 200)
        self.assertFalse(toggled.json()["skill"]["enabled"])

        selected = self.client.post("/api/models/select", json={"model": "llama3.1:8b"})
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["runtime"]["model"], "llama3.1:8b")

        deleted = self.client.delete(f"/api/skills/{skill_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])

    def test_settings_endpoints(self) -> None:
        settings_resp = self.client.get("/api/settings")
        self.assertEqual(settings_resp.status_code, 200)
        settings_payload = settings_resp.json()
        self.assertIn("settings", settings_payload)
        self.assertIn("model_folder_detection", settings_payload)
        self.assertIn("items", settings_payload["model_folder_detection"])
        self.assertIsNone(settings_payload["model_folder_detection"].get("detected_at"))

        models_dir = self.temp_path / "models"
        updated = self.client.put(
            "/api/settings",
            json={
                "theme": "ocean",
                "ollama_models_dir": str(models_dir),
                "ollama_base_url": "http://127.0.0.1:11434",
                "llm_history_limit": 18,
                "intent_confidence_threshold": 0.66,
                "auto_select_after_pull": False,
                "enter_to_send": False,
                "web_port_preferred": 8123,
            },
        )
        self.assertEqual(updated.status_code, 200)
        snapshot = updated.json()
        self.assertEqual(snapshot["settings"]["theme"], "ocean")
        self.assertEqual(snapshot["settings"]["llm_history_limit"], 18)
        self.assertAlmostEqual(snapshot["settings"]["intent_confidence_threshold"], 0.66, places=2)
        self.assertEqual(snapshot["settings"]["web_port_preferred"], 8123)
        self.assertFalse(snapshot["settings"]["auto_select_after_pull"])
        self.assertFalse(snapshot["settings"]["enter_to_send"])

        detected = self.client.post("/api/settings/model-folders/detect", json={})
        self.assertEqual(detected.status_code, 200)
        detection_payload = detected.json()["model_folder_detection"]
        self.assertIn("items", detection_payload)
        self.assertIsInstance(detection_payload["items"], list)
        self.assertIsNotNone(detection_payload.get("detected_at"))

    def test_openai_compatible_provider_settings(self) -> None:
        updated = self.client.put(
            "/api/settings",
            json={
                "llm_provider": "openai_compatible",
                "openai_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "openai_api_key": "test-api-key",
                "openai_model": "qwen-plus",
                "llm_model": "qwen-plus",
            },
        )
        self.assertEqual(updated.status_code, 200)
        payload = updated.json()["settings"]
        self.assertEqual(payload["llm_provider"], "openai_compatible")
        self.assertEqual(payload["openai_model"], "qwen-plus")
        self.assertTrue(payload["openai_has_api_key"])
        self.assertNotIn("openai_api_key", payload)

        runtime = self.client.get("/api/runtime")
        self.assertEqual(runtime.status_code, 200)
        self.assertEqual(runtime.json()["runtime"]["provider"], "openai_compatible")
        self.assertEqual(runtime.json()["runtime"]["model"], "qwen-plus")

        tags_resp = self.client.get("/api/model-library/qwen3.5/tags")
        self.assertEqual(tags_resp.status_code, 400)
        self.assertIn("不支持标签版本列表", tags_resp.json().get("detail", ""))

    def test_invalid_provider_rejected(self) -> None:
        resp = self.client.put(
            "/api/settings",
            json={
                "llm_provider": "not_a_provider",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("不支持的模型提供方", resp.json().get("detail", ""))

    def test_upload_and_send_message(self) -> None:
        created = self.client.post("/api/conversations", json={"title": "Upload Session"})
        self.assertEqual(created.status_code, 200)
        conversation_id = created.json()["conversation"]["id"]

        uploaded = self.client.post(
            "/api/uploads",
            files={"file": ("notes.txt", b"risk one\\nrisk two\\nmitigation", "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 200)
        upload_id = uploaded.json()["upload"]["id"]

        sent = self.client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={
                "content": "请根据附件列出风险",
                "upload_ids": [upload_id],
            },
        )
        self.assertEqual(sent.status_code, 200)
        payload = sent.json()
        self.assertIn("used_uploads", payload)
        self.assertEqual(len(payload["used_uploads"]), 1)

        listed = self.client.get(f"/api/conversations/{conversation_id}/messages")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any("[附件]" in item["content"] for item in listed.json()["items"]))

        deleted = self.client.delete(f"/api/uploads/{upload_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])

    def test_pull_stream_emits_start_event(self) -> None:
        models_dir = self.temp_path / "models"
        updated = self.client.put(
            "/api/settings",
            json={
                "ollama_models_dir": str(models_dir),
            },
        )
        self.assertEqual(updated.status_code, 200)

        stream_resp = self.client.post(
            "/api/models/pull",
            json={"model": "qwen3.5:4b", "select_after_pull": True},
        )
        self.assertEqual(stream_resp.status_code, 200)
        body = stream_resp.text.strip().splitlines()
        self.assertTrue(any('"type": "start"' in line for line in body))
        self.assertTrue(any('"target_dir"' in line for line in body if '"type": "start"' in line))
        self.assertTrue(any('"type": "error"' in line for line in body))

    def test_ollama_version_endpoint_shape(self) -> None:
        resp = self.client.get("/api/ollama/version")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn("base_url", payload)
        self.assertIn("service_reachable", payload)
        self.assertIn("service_version", payload)
        self.assertIn("cli_available", payload)
        self.assertIn("cli_version", payload)
        self.assertIn("detail", payload)


if __name__ == "__main__":
    unittest.main()
