"""
config.secure_credentials — Secure API credential storage.

Uses OS credential manager (Windows Credential Manager) as primary store.
Falls back to environment variables for development/CI environments.
This module intentionally does NOT read from provider.json to prevent
plaintext credential exposure in version-controlled files.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, cast

log = logging.getLogger(__name__)

_SERVICE_NAME = "workflow_mvp"
_USERNAME_API_KEY = "subscription_key"
_USERNAME_CHARGE_CODE = "charge_code"


def _try_import_keyring():
    """Lazily import keyring to avoid hard dependency at import time."""
    try:
        import keyring

        return keyring
    except ImportError:
        log.warning(
            "keyring library not installed. "
            "Credential Manager storage unavailable. "
            "Install with: pip install keyring"
        )
        return None


class SecureCredentialStore:
    """
    Abstraction over OS credential storage for Workbench API secrets.

    Priority order for credential resolution:
      1. OS Credential Manager (via keyring library)
      2. Environment variables
      3. Returns None (caller decides how to handle absence)
    """

    @staticmethod
    def get_api_key() -> Optional[str]:
        """
        Retrieve the Workbench API subscription key.

        Returns:
            The subscription key string, or None if not found.
        """
        keyring = _try_import_keyring()
        if keyring:
            try:
                value = cast(Optional[str], keyring.get_password(_SERVICE_NAME, _USERNAME_API_KEY))
                if value:
                    return value
            except Exception as e:
                log.debug("keyring get_password failed: %s", e)

        # Fall back to environment variable
        return os.environ.get("WORKBENCH_SUBSCRIPTION_KEY")

    @staticmethod
    def set_api_key(key: str) -> None:
        """
        Store the Workbench API subscription key in OS credential manager.

        Args:
            key: The subscription key to store.

        Raises:
            RuntimeError: If keyring is unavailable and storage cannot proceed.
        """
        keyring = _try_import_keyring()
        if keyring is None:
            raise RuntimeError(
                "keyring library required for secure storage. "
                "Alternatively, set WORKBENCH_SUBSCRIPTION_KEY environment variable."
            )
        keyring.set_password(_SERVICE_NAME, _USERNAME_API_KEY, key)
        log.info("Subscription key stored in OS Credential Manager.")

    @staticmethod
    def get_charge_code() -> Optional[str]:
        """
        Retrieve the KPMG charge code.

        Returns:
            The charge code string, or None if not found.
        """
        keyring = _try_import_keyring()
        if keyring:
            try:
                value = cast(
                    Optional[str],
                    keyring.get_password(_SERVICE_NAME, _USERNAME_CHARGE_CODE),
                )
                if value:
                    return value
            except Exception as e:
                log.debug("keyring get_password failed: %s", e)

        return os.environ.get("WORKBENCH_CHARGE_CODE")

    @staticmethod
    def set_charge_code(code: str) -> None:
        """
        Store the KPMG charge code in OS credential manager.

        Args:
            code: The charge code to store.
        """
        keyring = _try_import_keyring()
        if keyring is None:
            raise RuntimeError(
                "keyring library required for secure storage. "
                "Alternatively, set WORKBENCH_CHARGE_CODE environment variable."
            )
        keyring.set_password(_SERVICE_NAME, _USERNAME_CHARGE_CODE, code)
        log.info("Charge code stored in OS Credential Manager.")

    @staticmethod
    def has_credentials() -> bool:
        """
        Check whether both required credentials are available from any source.

        Returns:
            True if both subscription_key and charge_code are resolvable.
        """
        return (
            SecureCredentialStore.get_api_key() is not None
            and SecureCredentialStore.get_charge_code() is not None
        )
