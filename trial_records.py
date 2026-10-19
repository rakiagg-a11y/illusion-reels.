"""Small file helpers shared by the month-trial scripts."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time

from five_style_render import atomic_json


def read_json(path, default=None):
    """JSON from disk; UTF-8 with or without a byte-order mark."""
    path = Path(path)
    if not path.is_file():
        if default is None:
            raise FileNotFoundError(path)
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@contextmanager
def file_lock(path, wait=120):
    """Exclusive lock next to path; waits for a busy lock instead of failing at once."""
    lock = Path(str(path)+".lock")
    deadline = time.monotonic()+wait
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() > deadline:
                raise ValueError(f"{lock} is held by another process; inspect it before removing a stale lock") from None
            time.sleep(1)
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def update_json(path, change, default):
    """Read, change and atomically rewrite a shared record under its lock."""
    with file_lock(path):
        value = read_json(path, default)
        result = change(value)
        atomic_json(path, value)
        return result
