from __future__ import annotations

from pathlib import Path
import difflib


def unified_diff(path: str | Path, before: str, after: str) -> str:
    file_name = str(Path(path))
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{file_name} (before)",
            tofile=f"{file_name} (after)",
        )
    )
