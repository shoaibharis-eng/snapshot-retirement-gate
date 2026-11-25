"""One record of the instruction log, sealed into a hash chain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from verifier.hashing import digest
from verifier.log.scope import Scope

GENESIS = "0" * 64
"""The ``prev_hash`` of the first entry, and the head of an empty log."""


@dataclass(frozen=True)
class LogHead:
    """A position in the log: how many entries exist and the hash of the last."""

    seq: int
    entry_hash: str

    def to_json(self) -> dict[str, Any]:
        return {"seq": self.seq, "entry_hash": self.entry_hash}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> LogHead:
        return cls(seq=data["seq"], entry_hash=data["entry_hash"])


@dataclass(frozen=True)
class LogEntry:
    """A repair instruction together with the scope it was given."""

    seq: int
    issued_by: str
    instruction: str
    scope: Scope
    prev_hash: str
    entry_hash: str

    @classmethod
    def seal(
        cls, seq: int, issued_by: str, instruction: str, scope: Scope, prev_hash: str
    ) -> LogEntry:
        """Build an entry whose hash commits to its content and its predecessor."""
        unsealed = cls(seq, issued_by, instruction, scope, prev_hash, entry_hash="")
        return cls(seq, issued_by, instruction, scope, prev_hash, digest(unsealed._body()))

    def is_sealed(self) -> bool:
        return self.entry_hash == digest(self._body())

    def to_json(self) -> dict[str, Any]:
        return {**self._body(), "entry_hash": self.entry_hash}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> LogEntry:
        return cls(
            seq=data["seq"],
            issued_by=data["issued_by"],
            instruction=data["instruction"],
            scope=Scope.from_json(data["scope"]),
            prev_hash=data["prev_hash"],
            entry_hash=data["entry_hash"],
        )

    def _body(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "issued_by": self.issued_by,
            "instruction": self.instruction,
            "scope": self.scope.to_json(),
            "prev_hash": self.prev_hash,
        }
