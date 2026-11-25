"""Work out the scope decision the gate needs from a human.

When the repair changed something no log entry covers, the gate cannot decide
on its own. It names the boundaries that changed without a scope and, where
the diff looks like a move, drafts the scope that would authorise it. The draft
is inferred from the implementation, so it is only ever a question for a human.
"""

from __future__ import annotations

from verifier.gate.decision import ScopeRequest
from verifier.gate.delta import ChangeKind
from verifier.gate.evidence import Evidence
from verifier.log import Rename
from verifier.snapshot import Symbol


def build_scope_request(evidence: Evidence) -> ScopeRequest | None:
    uncovered = evidence.provenance.uncovered()
    if evidence.log_problem or not uncovered:
        return None
    removed = [c.subject for c in uncovered if c.kind is ChangeKind.SYMBOL_REMOVED]
    added = [c.subject for c in uncovered if c.kind is ChangeKind.SYMBOL_ADDED]
    suggested = []
    for old in removed:
        successor = _likely_successor(evidence.snapshot.topology.symbols[old], added, evidence)
        if successor is not None:
            suggested.append(Rename(old, successor))
    boundaries = tuple(
        change.subject for change in evidence.boundary_changes() if change in uncovered
    )
    return ScopeRequest(boundaries, tuple(suggested))


def _likely_successor(old: Symbol, added: list[str], evidence: Evidence) -> str | None:
    """The one added symbol that could be ``old`` under a new name, if any."""
    symbols = evidence.observed.symbols
    same_interface = [name for name in added if symbols[name].interface() == old.interface()]
    same_body = [name for name in same_interface if symbols[name].fingerprint == old.fingerprint]
    candidates = same_body or same_interface
    return candidates[0] if len(candidates) == 1 else None
