"""Participant-side file guard for evaluator-only manifest isolation.

The benchmark executes trusted participant implementations in one thread. During
participant decisions, direct Python file access to registered hidden artifacts is
denied in addition to withholding hidden objects from the method interface.
"""

from __future__ import annotations

import builtins
import contextlib
import io
import os
from pathlib import Path
from typing import Any, Iterator


@contextlib.contextmanager
def participant_file_guard(*hidden_paths: Path) -> Iterator[None]:
    protected = {path.resolve() for path in hidden_paths}
    original_builtin_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open

    def deny_if_protected(file: Any) -> None:
        if isinstance(file, int):
            return
        try:
            resolved = Path(file).resolve()
        except (OSError, TypeError, ValueError):
            return
        if resolved in protected or resolved.name == "hidden_world_manifest.json":
            raise PermissionError(f"Participant access to evaluator-only artifact denied: {resolved}")

    def guarded_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        deny_if_protected(file)
        return original_builtin_open(file, *args, **kwargs)

    def guarded_io_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        deny_if_protected(file)
        return original_io_open(file, *args, **kwargs)

    def guarded_os_open(file: Any, *args: Any, **kwargs: Any) -> int:
        deny_if_protected(file)
        return original_os_open(file, *args, **kwargs)

    builtins.open = guarded_open
    io.open = guarded_io_open
    os.open = guarded_os_open
    try:
        yield
    finally:
        builtins.open = original_builtin_open
        io.open = original_io_open
        os.open = original_os_open
