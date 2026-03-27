"""
core.provider — Workbench API client.

Wraps the KPMG Workbench (Azure OpenAI) HTTP call behind a clean
interface.  Returns ProviderResponse with content, metrics, and
raw JSON for tracing.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import requests

from core.models import ProviderRequest, ProviderResponse


class WorkbenchClient:
    """HTTP client for the Workbench GenAI API."""

    def __init__(
        self,
        base_url: str,
        subscription_key: str,
        charge_code: str,
        api_version: str = "2024-06-01",
        timeout: int = 300,
        use_ntlm: bool = False,
        ntlm_user: Optional[str] = None,
        ntlm_password: Optional[str] = None,
        model_overrides: Optional[dict[str, Any]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.subscription_key = subscription_key
        self.charge_code = charge_code
        self.api_version = api_version
        self.model_overrides = dict(model_overrides) if model_overrides else {}
        self.timeout = timeout
        self.use_ntlm = use_ntlm
        self.ntlm_user = ntlm_user
        self.ntlm_password = ntlm_password
        self._session = requests.Session()

        # Set default headers on the session
        self._session.headers.update(
            {
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "x-kpmg-charge-code": self.charge_code,
                "Content-Type": "application/json",
            }
        )

        # Optional NTLM auth
        if self.use_ntlm and self.ntlm_user:
            try:
                from requests_ntlm import HttpNtlmAuth

                self._session.auth = HttpNtlmAuth(
                    self.ntlm_user, self.ntlm_password or ""
                )
            except ImportError:
                pass  # NTLM not available; proceed without

    @classmethod
    def from_config(cls, config: dict) -> "WorkbenchClient":
        """
        Create a client from a config dict (loaded from provider.json).

        Credential resolution priority:
          1. provider.json fields: subscription_key / charge_code
          2. OS Credential Manager / environment variables (via SecureCredentialStore)
          3. Empty string if unavailable (caller decides readiness)
        """
        from config.secure_credentials import SecureCredentialStore

        # Prefer explicit values from provider.json when provided.
        subscription_key = config.get("subscription_key") or ""
        charge_code = config.get("charge_code") or ""

        # Fall back to secure store / env if missing from config.
        if not subscription_key:
            subscription_key = SecureCredentialStore.get_api_key() or ""
        if not charge_code:
            charge_code = SecureCredentialStore.get_charge_code() or ""

        default_ver = config.get("default_api_version") or config.get(
            "api_version", "2024-06-01"
        )
        overrides = config.get("model_overrides") or {}

        return cls(
            base_url=config.get("base_url", ""),
            subscription_key=subscription_key,
            charge_code=charge_code,
            api_version=default_ver,
            timeout=config.get("timeout", 300),
            use_ntlm=config.get("use_ntlm", False),
            ntlm_user=config.get("ntlm_user"),
            ntlm_password=config.get("ntlm_password"),
            model_overrides=overrides,
        )

    def _api_version_for_model(self, model: str) -> str:
        entry = self.model_overrides.get(model)
        if isinstance(entry, dict):
            ver = entry.get("api_version")
            if ver:
                return str(ver)
        return self.api_version

    def _build_url(self, model: str) -> str:
        """Construct the chat completions endpoint URL."""
        ver = self._api_version_for_model(model)
        return (
            f"{self.base_url}/deployments/{model}/chat/completions"
            f"?api-version={ver}"
        )

    def chat_completion(self, req: ProviderRequest) -> ProviderResponse:
        """
        Send a chat completion request and return a structured response.

        Captures latency, parses content and usage from the Azure OpenAI
        response format, and wraps errors cleanly.
        """
        url = self._build_url(req.model)
        body = {"messages": req.messages}

        try:
            resp = self._session.post(
                url,
                json=body,
                timeout=req.timeout or self.timeout,
            )

            # Try to parse JSON regardless of status code
            try:
                raw_json = resp.json()
            except (json.JSONDecodeError, ValueError):
                raw_json = {"_raw_text": resp.text}

            if resp.status_code >= 400:
                error_msg = raw_json.get("error", {}).get("message", resp.text[:500])
                return ProviderResponse(
                    raw_json=raw_json,
                    status_code=resp.status_code,
                    error=f"HTTP {resp.status_code}: {error_msg}",
                )

            # Extract content from Azure OpenAI response
            choices = raw_json.get("choices", [])
            content = ""
            if choices:
                content = choices[0].get("message", {}).get("content", "")

            # Extract usage if present
            usage = raw_json.get("usage")

            return ProviderResponse(
                content=content,
                raw_json=raw_json,
                usage=usage,
                status_code=resp.status_code,
            )

        except requests.exceptions.Timeout:
            return ProviderResponse(
                status_code=0,
                error=f"Request timed out after {req.timeout or self.timeout}s",
            )
        except requests.exceptions.RequestException as e:
            return ProviderResponse(
                status_code=0,
                error=f"Request failed: {e}",
            )

    def list_available_models(self) -> list[str]:
        """
        Return configured model names.  In this MVP the model list comes
        from config/models.json, not from an API call.  This method is a
        placeholder for potential future discovery.
        """
        return []
