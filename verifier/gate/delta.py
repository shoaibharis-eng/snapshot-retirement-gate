"""The interface delta: how the project's shape differs from the snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from verifier.snapshot import Topology


class ChangeKind(Enum):
    SYMBOL_REMOVED = "symbol removed"
    SYMBOL_ADDED = "symbol added"
    SIGNATURE_CHANGED = "signature changed"
    IMPORT_REMOVED = "import removed"
    IMPORT_ADDED = "import added"


IMPORT_KINDS = (ChangeKind.IMPORT_REMOVED, ChangeKind.IMPORT_ADDED)


@dataclass(frozen=True)
class Change:
    """One atomic difference between two topologies.

    For symbol changes ``subject`` is the symbol and ``detail`` describes a
    signature change. For import changes ``subject`` is the importing module
    and ``detail`` is the name it imports.
    """

    kind: ChangeKind
    subject: str
    detail: str = ""

    def describe(self) -> str:
        if self.kind in IMPORT_KINDS:
            return f"{self.kind.value}: {self.subject} imports {self.detail}"
        if self.kind is ChangeKind.SIGNATURE_CHANGED:
            return f"{self.kind.value}: {self.subject} {self.detail}"
        return f"{self.kind.value}: {self.subject}"


def interface_delta(before: Topology, after: Topology) -> tuple[Change, ...]:
    """Every public symbol and internal import that differs, in a stable order."""
    changes = []
    for name in sorted(before.symbols.keys() | after.symbols.keys()):
        old, new = before.symbols.get(name), after.symbols.get(name)
        if new is None:
            changes.append(Change(ChangeKind.SYMBOL_REMOVED, name))
        elif old is None:
            changes.append(Change(ChangeKind.SYMBOL_ADDED, name))
        elif old.interface() != new.interface():
            detail = f"{old.signature} became {new.signature}"
            changes.append(Change(ChangeKind.SIGNATURE_CHANGED, name, detail))
    for module in sorted(before.imports.keys() | after.imports.keys()):
        was = set(before.imports.get(module, ()))
        now = set(after.imports.get(module, ()))
        changes.extend(Change(ChangeKind.IMPORT_REMOVED, module, t) for t in sorted(was - now))
        changes.extend(Change(ChangeKind.IMPORT_ADDED, module, t) for t in sorted(now - was))
    return tuple(changes)
