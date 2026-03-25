"""
Workflow MVP — Application Entry Point.

Launches the tkinter-based AI workflow runner.
Falls back to a console message if tkinter is unavailable.
"""

import sys
from pathlib import Path

# Project root = directory containing this file
PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Entry point: check tkinter, then launch the app."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "ERROR: tkinter is not available in this Python installation.\n"
            "Install it or use a Python distribution that includes tkinter.\n"
            "On Ubuntu/Debian: sudo apt install python3-tk\n"
            "On Windows: tkinter is included with the standard installer.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Ensure config directory exists
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "prompts").mkdir(exist_ok=True)

    # Ensure runs directory exists
    (PROJECT_ROOT / "runs").mkdir(exist_ok=True)

    # Check provider config
    provider_config = config_dir / "provider.json"
    if not provider_config.is_file():
        print(
            "NOTE: config/provider.json not found.\n"
            "Create it with your Workbench API credentials to enable API calls.\n"
            "Example:\n"
            "{\n"
            '  "base_url": "https://api.workbench.kpmg/genai/azure/openai",\n'
            '  "subscription_key": "your-key",\n'
            '  "charge_code": "your-code",\n'
            '  "api_version": "2024-06-01",\n'
            '  "timeout": 300\n'
            "}\n",
        )

    from ui.app import App

    app = App(PROJECT_ROOT)
    app.run()


if __name__ == "__main__":
    main()
