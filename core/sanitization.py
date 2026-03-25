"""
core.sanitization — Output sanitization utilities for display safety.

This module sanitizes text produced by LLM models before rendering in the UI.
Sanitization happens ONLY at the display boundary — raw results are stored
unmodified to preserve complete debug information.

Key concern for this desktop application (Tkinter-based):
  - No XSS risk (Tkinter does not interpret HTML/JS)
  - Real risk: ANSI terminal escape sequences corrupting ScrolledText widgets
  - Real risk: Null bytes causing truncation in string operations
"""

from __future__ import annotations

import re

# ANSI escape sequence pattern (e.g. \x1b[31m for red, \x1b[0m for reset)
_ANSI_ESCAPE_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-9;]*[ -/]*[@-~])")

# Maximum byte size for log-safe output (10 KB)
_MAX_LOG_BYTES = 10 * 1024


def sanitize_for_display(text: str) -> str:
    """
    Sanitize LLM output text for safe rendering in Tkinter ScrolledText widgets.

    Removes:
      - ANSI terminal escape sequences (e.g., color codes like \\x1b[31m)
      - Null bytes (\\x00) which can silently truncate strings
      - Other C0 control characters below space, except \\n \\t \\r

    Preserves:
      - Newlines, tabs, carriage returns (needed for layout)
      - All printable unicode characters
      - Markdown syntax (Tkinter renders it as literal text, no harm done)

    Args:
        text: Raw string from LLM model output.

    Returns:
        Cleaned string safe for direct insertion into Tkinter text widgets.

    Examples:
        >>> sanitize_for_display("\\x1b[31mred text\\x1b[0m")
        'red text'
        >>> sanitize_for_display("hello\\x00world")
        'helloworld'
    """
    if not text:
        return text

    # Remove ANSI escape sequences
    result = _ANSI_ESCAPE_RE.sub("", text)

    # Remove control characters except newline (0x0A), tab (0x09), carriage return (0x0D)
    result = "".join(ch for ch in result if ord(ch) >= 32 or ch in ("\n", "\t", "\r"))

    return result


def sanitize_log_output(text: str) -> str:
    """
    Sanitize LLM output for safe writing to log files and terminal output.

    Same as ``sanitize_for_display`` but also truncates to 10 KB to prevent
    oversized log entries from bloating log files.

    Args:
        text: Raw string from LLM model output.

    Returns:
        Cleaned, size-bounded string safe for logging.

    Examples:
        >>> result = sanitize_log_output("\\x1b[0m" + "A" * 20000)
        >>> result.endswith("[truncated]")
        True
    """
    cleaned = sanitize_for_display(text)

    encoded = cleaned.encode("utf-8", errors="replace")
    if len(encoded) > _MAX_LOG_BYTES:
        truncated = encoded[:_MAX_LOG_BYTES].decode("utf-8", errors="replace")
        return truncated + " [truncated]"

    return cleaned
