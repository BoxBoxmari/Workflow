"""Tests for core.provider — Workbench API client (mocked)."""

import unittest
from unittest.mock import MagicMock, patch

from core.models import ProviderRequest
from core.provider import WorkbenchClient


class TestWorkbenchClient(unittest.TestCase):
    def setUp(self):
        self.client = WorkbenchClient(
            base_url="https://api.test.local/genai/azure/openai",
            subscription_key="test-key",
            charge_code="test-code",
            api_version="2024-06-01",
            timeout=30,
        )

    def test_build_url(self):
        url = self.client._build_url("gpt-4o")
        self.assertIn("/deployments/gpt-4o/chat/completions", url)
        self.assertIn("api-version=2024-06-01", url)

    def test_build_url_respects_model_override(self):
        client = WorkbenchClient(
            base_url="https://api.test.local/genai/azure/openai",
            subscription_key="test-key",
            charge_code="test-code",
            api_version="2024-06-01",
            timeout=30,
            model_overrides={
                "gpt-5-2025-08-07-gs-ae": {"api_version": "2025-01-01-preview"},
            },
        )
        url = client._build_url("gpt-5-2025-08-07-gs-ae")
        self.assertIn("api-version=2025-01-01-preview", url)
        url_default = client._build_url("gpt-4o")
        self.assertIn("api-version=2024-06-01", url_default)

    def test_headers_set(self):
        self.assertEqual(
            self.client._session.headers["Ocp-Apim-Subscription-Key"],
            "test-key",
        )
        self.assertEqual(
            self.client._session.headers["x-kpmg-charge-code"],
            "test-code",
        )

    @patch("core.provider.requests.Session.post")
    def test_chat_completion_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_post.return_value = mock_resp

        req = ProviderRequest(
            model="gpt-4o", messages=[{"role": "user", "content": "Hi"}]
        )
        resp = self.client.chat_completion(req)

        self.assertTrue(resp.ok)
        self.assertEqual(resp.content, "Hello!")
        self.assertEqual(resp.usage["total_tokens"], 15)
        self.assertEqual(resp.status_code, 200)

    @patch("core.provider.requests.Session.post")
    def test_chat_completion_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"error": {"message": "Rate limited"}}
        mock_resp.text = "Rate limited"
        mock_post.return_value = mock_resp

        req = ProviderRequest(
            model="gpt-4o", messages=[{"role": "user", "content": "Hi"}]
        )
        resp = self.client.chat_completion(req)

        self.assertFalse(resp.ok)
        self.assertIn("429", resp.error)

    @patch("core.provider.requests.Session.post")
    def test_chat_completion_timeout(self, mock_post):
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("timeout")

        req = ProviderRequest(
            model="gpt-4o", messages=[{"role": "user", "content": "Hi"}]
        )
        resp = self.client.chat_completion(req)

        self.assertFalse(resp.ok)
        self.assertIn("timed out", resp.error)

    def test_from_config(self):
        config = {
            "base_url": "https://test.local",
            "subscription_key": "key",
            "charge_code": "code",
        }
        client = WorkbenchClient.from_config(config)
        self.assertEqual(client.base_url, "https://test.local")

    def test_from_config_default_api_version_and_model_overrides(self):
        config = {
            "base_url": "https://test.local",
            "subscription_key": "key",
            "charge_code": "code",
            "default_api_version": "2024-06-01",
            "model_overrides": {
                "m-special": {"api_version": "2025-01-01-preview"},
            },
        }
        client = WorkbenchClient.from_config(config)
        self.assertEqual(client.api_version, "2024-06-01")
        self.assertEqual(
            client.model_overrides["m-special"]["api_version"],
            "2025-01-01-preview",
        )
        self.assertIn("2025-01-01-preview", client._build_url("m-special"))

    def test_from_config_legacy_api_version_key(self):
        config = {
            "base_url": "https://test.local",
            "subscription_key": "key",
            "charge_code": "code",
            "api_version": "2024-08-01-preview",
        }
        client = WorkbenchClient.from_config(config)
        self.assertEqual(client.api_version, "2024-08-01-preview")


if __name__ == "__main__":
    unittest.main()
