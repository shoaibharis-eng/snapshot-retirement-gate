"""The "what the gate saw" part of a trace: records, delta and suite runs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from verifier.gate import AuthorisedRename, Change, ChangeKind, Evidence
from verifier.hashing import short
from verifier.suite import PASS, UNLOADABLE, Outcome
from verifier.trace.markdown import code_list, table


def snapshot(evidence: Evidence) -> str:
    frozen = evidence.snapshot
    files = [file for file in frozen.suite if file.tests]
    return (
        f"**Snapshot** `{short(frozen.id)}`: {len(files)} frozen test files, "
        f"{frozen.test_count()} tests, pinned to {code_list(frozen.boundaries())}."
    )


def log(evidence: Evidence) -> str:
    if evidence.log_problem:
        return f"**Instruction log**: not trusted. {evidence.log_problem}."
    lines = ["**Instruction log since the freeze**", ""]
    for entry in evidence.entries:
        lines.append(f'- entry #{entry.seq}, issued by `{entry.issued_by}`: "{entry.instruction}"')
        lines.append(f"  - scope: {entry.scope.describe()}")
    if not evidence.entries:
        lines.append("- no entries")
    return "\n".join(lines)


def delta(evidence: Evidence) -> str:
    if not evidence.delta:
        return "**Interface delta**: none. The project has the shape it had at the freeze."
    rows = []
    for change in evidence.delta:
        seq = evidence.provenance.authoriser_of(change)
        authority = f"entry #{seq}" if seq is not None else "**no entry**"
        rows.append((change.kind.value, _where(change, evidence), authority))
    listing = table(("Change", "Where", "Authorised by"), rows)
    return f"**Interface delta** (snapshot to repaired project)\n\n{listing}"


def suite(evidence: Evidence) -> str:
    if evidence.as_frozen is None:
        return "**Frozen suite**: not run, because it is no longer the frozen suite."
    rows = []
    for file in evidence.snapshot.suite:
        if not file.tests:
            continue
        as_frozen = _tally(evidence.as_frozen.for_file(file.path))
        rebound = _tally(evidence.rebound.for_file(file.path)) if evidence.rebound else "not run"
        rows.append((f"`{file.path}`", code_list(file.pins), as_frozen, rebound))
    headers = ("Frozen file", "Pinned to", "Exactly as frozen", "Re-bound through the log")
    lines = ["**Frozen suite** (the files are never modified)", "", table(headers, rows)]
    if evidence.rebound is not None:
        lines += [""] + [
            _rebinding_note(rename, evidence) for rename in evidence.provenance.exercised
        ]
    return "\n".join(lines)


def _where(change: Change, evidence: Evidence) -> str:
    if change.kind in (ChangeKind.IMPORT_REMOVED, ChangeKind.IMPORT_ADDED):
        return f"`{change.subject}` imports `{change.detail}`"
    where = f"`{change.subject}`"
    if change.kind is ChangeKind.SIGNATURE_CHANGED:
        where += f": `{change.detail}`"
    if change.kind is not ChangeKind.SYMBOL_ADDED and evidence.snapshot.is_boundary(change.subject):
        where += " (boundary)"
    return where


def _rebinding_note(rename: AuthorisedRename, evidence: Evidence) -> str:
    body = "changed" if rename.old in evidence.rewritten else "unchanged"
    return (
        f"- Re-binding: `{rename.old}` resolves to `{rename.new}` (entry #{rename.entry_seq}). "
        f"Body compared with the freeze: {body}."
    )


def _tally(outcomes: Sequence[Outcome]) -> str:
    """For example ``4 pass, 1 fail`` or ``5 cannot load (ImportError)``."""
    counts = Counter(outcome.status for outcome in outcomes)
    parts = []
    if counts[PASS]:
        parts.append(f"{counts[PASS]} pass")
    if counts[UNLOADABLE]:
        reason = next(o.reason for o in outcomes if o.status == UNLOADABLE)
        parts.append(f"{counts[UNLOADABLE]} cannot load ({reason})")
    failed = len(outcomes) - counts[PASS] - counts[UNLOADABLE]
    if failed:
        parts.append(f"{failed} fail")
    return ", ".join(parts)
