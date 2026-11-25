"""The append-only instruction log.

Stored as JSON Lines, one sealed entry per line, outside both the code and the
test suite. The class offers no way to edit or remove an entry, and every read
re-verifies the hash chain, so an edit made behind its back is detected.
"""

from __future__ import annotations

import json
from pathlib import Path

from verifier.hashing import canonical_json
from verifier.log.entry import GENESIS, LogEntry, LogHead
from verifier.log.scope import Scope, ScopeError


class LogIntegrityError(Exception):
    """Raised when the stored log is not an unbroken, append-only chain."""


class InstructionLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, issued_by: str, instruction: str, scope: Scope) -> LogEntry:
        """Record an instruction and its scope at the end of the log."""
        entries = self.entries()
        prev_hash = entries[-1].entry_hash if entries else GENESIS
        entry = LogEntry.seal(len(entries) + 1, issued_by, instruction, scope, prev_hash)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(entry.to_json()) + "\n")
        return entry

    def entries(self) -> tuple[LogEntry, ...]:
        """Every entry, oldest first, after verifying the whole chain."""
        if not self.path.exists():
            return ()
        entries: list[LogEntry] = []
        prev_hash = GENESIS
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            entry = _parse(line, number)
            if entry.seq != number:
                raise LogIntegrityError(f"line {number} holds entry #{entry.seq}")
            if entry.prev_hash != prev_hash:
                raise LogIntegrityError(f"entry #{number} does not follow entry #{number - 1}")
            if not entry.is_sealed():
                raise LogIntegrityError(f"entry #{number} was altered after it was recorded")
            entries.append(entry)
            prev_hash = entry.entry_hash
        return tuple(entries)

    def head(self) -> LogHead:
        entries = self.entries()
        if not entries:
            return LogHead(0, GENESIS)
        return LogHead(entries[-1].seq, entries[-1].entry_hash)

    def entries_after(self, anchor: LogHead) -> tuple[LogEntry, ...]:
        """Entries appended since ``anchor``, proving the log still extends it."""
        entries = self.entries()
        if anchor.seq > len(entries):
            raise LogIntegrityError(
                f"the log has {len(entries)} entries but had {anchor.seq} at the anchor"
            )
        anchored = entries[anchor.seq - 1].entry_hash if anchor.seq else GENESIS
        if anchored != anchor.entry_hash:
            raise LogIntegrityError("the log was rewritten before the anchor")
        return entries[anchor.seq :]


def _parse(line: str, number: int) -> LogEntry:
    try:
        return LogEntry.from_json(json.loads(line))
    except (ValueError, KeyError, TypeError, ScopeError) as error:
        raise LogIntegrityError(f"line {number} is not a log entry: {error}") from error
