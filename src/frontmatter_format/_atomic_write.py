"""
Atomic text file writes, for the frontmatter writers.
"""

import os
import secrets
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

_TEMP_NAME_ATTEMPTS = 100


def _create_temp_file(path: Path, label: str) -> tuple[TextIO, Path]:
    """
    Create and open a new, uniquely named temp file in the directory of `path`, so it can
    be renamed over `path` atomically.

    Exclusive creation (`open` mode `"x"`) never reuses a file another writer made, and
    gives the file the mode any new file gets (0o666 less the umask). `tempfile.mkstemp`
    would always make it 0o600.
    """
    for _ in range(_TEMP_NAME_ATTEMPTS):
        temp_path = path.parent / f"{path.name}.fmf.{label}.{secrets.token_hex(4)}.tmp"
        try:
            return open(temp_path, "x", encoding="utf-8"), temp_path
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not create a unique temp file beside `{path}`")


@contextmanager
def atomic_write_text(path: str | Path, label: str) -> Generator[TextIO, None, None]:
    """
    Write UTF-8 text to `path` atomically.

    Yields a text stream on a new temp file beside `path`. When the block ends without an
    error, gives the temp file the mode of the file at `path`, if there is one and the
    filesystem allows it, and renames it over `path`. On any error, removes the temp file
    and leaves `path` as it was.
    Readers see the old file or the new one, never part of a write, and concurrent writers
    each write their own temp file, so the last rename wins.
    """
    path = Path(path)
    stream, temp_path = _create_temp_file(path, label)
    try:
        with stream:
            yield stream
        try:
            shutil.copymode(path, temp_path)
        except OSError:
            # With no file at `path` yet, the new file keeps the default mode the temp file
            # was created with. That is also the fallback on a filesystem that refuses
            # chmod (some FUSE mounts), which still gets the write.
            pass
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
