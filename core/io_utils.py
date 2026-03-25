"""
core.io_utils — Atomic file write helpers.

Prevents config corruption by writing to a temporary file first,
then renaming atomically.  Falls back to direct write on platforms
where os.replace is not truly atomic (Windows NTFS is close enough).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def atomic_write_text(
    path: Path, content: str, encoding: str = "utf-8", max_retries: int = 3
) -> None:
    """
    Write *content* to *path* atomically via temp-file + rename.

    Uses exponential back-off retry on ``PermissionError`` to handle the
    common Windows scenario where the target file is briefly held open by
    another process (e.g. the user has a .json file open in Notepad/Excel).

    Args:
        path:        Destination file path.
        content:     Text content to write.
        encoding:    File encoding (default: utf-8).
        max_retries: Maximum rename attempts before re-raising (default: 3).

    Raises:
        PermissionError: If the file remains locked after all retries.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.stem}_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)

        for attempt in range(max_retries):
            try:
                os.replace(tmp_path, str(path))
                return
            except PermissionError:
                if attempt == max_retries - 1:
                    raise
                wait = 0.5 * (attempt + 1)  # 0.5s → 1.0s → raise
                time.sleep(wait)
    except BaseException:
        # Clean up temp file on any failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(
    path: Path,
    data: Any,
    *,
    indent: int = 2,
    encoding: str = "utf-8",
    ensure_ascii: bool = False,
) -> None:
    """Serialize *data* as JSON and write atomically to *path*."""
    content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
    atomic_write_text(path, content + "\n", encoding=encoding)
