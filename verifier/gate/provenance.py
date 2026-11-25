"""Provenance: which log entry, if any, each interface change traces back to.

The agent's own account of a repair is never consulted. Provenance is worked
out from two things the agent does not control: the scopes in the instruction
log and the observed interface delta.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from verifier.gate.delta import IMPORT_KINDS, Change, ChangeKind
from verifier.log import LogEntry
from verifier.snapshot import Topology, module_of


@dataclass(frozen=True)
class AuthorisedRename:
    """A rename the log allows, from a name in the snapshot to a current name."""

    old: str
    new: str
    entry_seq: int


@dataclass(frozen=True)
class Attribution:
    change: Change
    entry_seq: int | None
    """The entry whose scope covers the change, or None if nothing does."""


@dataclass(frozen=True)
class Provenance:
    attributions: tuple[Attribution, ...]
    exercised: tuple[AuthorisedRename, ...]
    """Authorised renames the repair actually carried out."""
    violations: tuple[str, ...]
    """Ways a carried-out rename is not what its scope describes."""

    def authoriser_of(self, change: Change) -> int | None:
        return next((a.entry_seq for a in self.attributions if a.change == change), None)

    def uncovered(self) -> tuple[Change, ...]:
        return tuple(a.change for a in self.attributions if a.entry_seq is None)

    def bindings(self) -> dict[str, str]:
        """Retired name to successor, for replaying the frozen suite."""
        return {rename.old: rename.new for rename in self.exercised}


def trace_provenance(
    delta: Sequence[Change], entries: Sequence[LogEntry], before: Topology, after: Topology
) -> Provenance:
    exercised = tuple(
        rename
        for rename in net_renames(entries)
        if rename.old in before.symbols and rename.old not in after.symbols
    )
    violations = []
    for rename in exercised:
        successor = after.symbols.get(rename.new)
        if successor is None:
            violations.append(
                f"entry #{rename.entry_seq} renames {rename.old} to {rename.new}, "
                f"but {rename.new} does not exist"
            )
        elif successor.interface() != before.symbols[rename.old].interface():
            violations.append(
                f"{rename.new} does not keep the signature of {rename.old}: "
                f"{before.symbols[rename.old].signature} became {successor.signature}"
            )
        violations += [
            f"{module} still imports {rename.old}, which entry #{rename.entry_seq} renamed away"
            for module, targets in after.imports.items()
            if rename.old in targets
        ]
    attributions = tuple(Attribution(change, _authoriser(change, exercised)) for change in delta)
    return Provenance(attributions, exercised, tuple(violations))


def net_renames(entries: Sequence[LogEntry]) -> list[AuthorisedRename]:
    """Fold the log's renames, in order, into net renames from snapshot names.

    ``a -> b`` followed by ``b -> c`` nets out to ``a -> c``, credited to the
    later entry. If two entries rename the same name, the later one wins.
    """
    net: dict[str, AuthorisedRename] = {}
    for entry in entries:
        for rename in entry.scope.renames:
            origin = next((o for o, r in net.items() if r.new == rename.old), rename.old)
            net[origin] = AuthorisedRename(origin, rename.new, entry.seq)
    return [rename for rename in net.values() if rename.old != rename.new]


def _authoriser(change: Change, exercised: Sequence[AuthorisedRename]) -> int | None:
    for rename in exercised:
        if change.kind is ChangeKind.SYMBOL_REMOVED and change.subject == rename.old:
            return rename.entry_seq
        if change.kind is ChangeKind.SYMBOL_ADDED and change.subject == rename.new:
            return rename.entry_seq
        if change.kind in IMPORT_KINDS and _is_rewiring(change, rename):
            return rename.entry_seq
    return None


def _is_rewiring(change: Change, rename: AuthorisedRename) -> bool:
    """True for the import changes a rename entails.

    That is: any import change inside the two modules the rename touches, and
    any module swapping its import of the old name for the new one.
    """
    old_module, new_module = module_of(rename.old), module_of(rename.new)
    if change.subject in (old_module, new_module):
        return True
    if change.kind is ChangeKind.IMPORT_REMOVED:
        return change.detail in (rename.old, old_module)
    return change.detail in (rename.new, new_module)
