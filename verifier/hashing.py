"""Canonical JSON and SHA-256 helpers shared by the log and the snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    """Serialise ``value`` so that equal content always yields equal text."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    """SHA-256 of the canonical JSON form of ``value``."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def short(full_digest: str) -> str:
    """A prefix long enough to identify a digest in a report."""
    return full_digest[:12]
