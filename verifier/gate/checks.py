"""The conditions of the retirement gate, one function each.

``integrity`` is a precondition. ``authorised``, ``contained`` and
``confined`` are the three agreed conditions. ``preserved`` is the further
evidence: an authorised rename retires a name, and this check finds out
whether the behaviour behind the name survived.
"""

from __future__ import annotations

from verifier.gate.decision import Finding, Status
from verifier.gate.evidence import Evidence
from verifier.suite import UNLOADABLE

QUESTIONS = {
    "integrity": "Are the frozen suite and the instruction log the ones that were recorded?",
    "authorised": "Does a log entry's scope cover every boundary change?",
    "contained": "Does the whole interface delta stay inside the declared scope?",
    "confined": "Does the frozen suite fail only on the changed boundary?",
    "preserved": "Re-bound through the log, does the frozen suite still pass?",
}


def run_checks(evidence: Evidence) -> tuple[Finding, ...]:
    checks = (integrity, authorised, contained, confined, preserved)
    return tuple(check(evidence) for check in checks)


def integrity(evidence: Evidence) -> Finding:
    problems = list(evidence.suite_drift)
    if evidence.log_problem:
        problems.insert(0, evidence.log_problem)
    if problems:
        return _finding("integrity", Status.FAIL, "The recorded evidence was altered.", problems)
    return _finding(
        "integrity",
        Status.PASS,
        "The frozen suite is byte-identical to the snapshot and the log extends its anchor.",
    )


def authorised(evidence: Evidence) -> Finding:
    if evidence.log_problem:
        return _finding("authorised", Status.SKIPPED, "An untrusted log cannot authorise anything.")
    boundary = evidence.boundary_changes()
    if not boundary:
        return _finding("authorised", Status.PASS, "No boundary changed.")
    orphans = [c for c in boundary if evidence.provenance.authoriser_of(c) is None]
    if orphans:
        summary = "No log entry's scope covers a boundary change."
        return _finding("authorised", Status.FAIL, summary, [c.describe() for c in orphans])
    summary = "Every boundary change traces back to a scoped log entry."
    return _finding("authorised", Status.PASS, summary)


def contained(evidence: Evidence) -> Finding:
    if evidence.log_problem:
        return _finding("contained", Status.SKIPPED, "An untrusted log declares no scope.")
    outside = [change.describe() for change in evidence.provenance.uncovered()]
    outside += evidence.provenance.violations
    if outside:
        summary = "The interface delta is not what the log allows."
        return _finding("contained", Status.FAIL, summary, outside)
    if not evidence.delta:
        return _finding("contained", Status.PASS, "The interface did not change.")
    summary = f"All {len(evidence.delta)} interface changes are inside the declared scope."
    return _finding("contained", Status.PASS, summary)


def confined(evidence: Evidence) -> Finding:
    if evidence.as_frozen is None:
        summary = "The suite was modified, so its results are not evidence."
        return _finding("confined", Status.SKIPPED, summary)
    failures = evidence.as_frozen.failures()
    if not failures:
        return _finding("confined", Status.PASS, "The frozen suite passes exactly as frozen.")
    changed = [change.subject for change in evidence.boundary_changes()]
    pinned = {
        file.path
        for file in evidence.snapshot.suite
        if any(file.is_pinned_to(symbol) for symbol in changed)
    }
    # A failure is on the boundary only if the test could not even be loaded
    # and its file imports a changed boundary. Anything else is behaviour.
    stray = [o for o in failures if o.status != UNLOADABLE or o.file not in pinned]
    if stray:
        summary = f"Frozen tests failing away from the changed boundary: {len(stray)}."
        return _finding("confined", Status.FAIL, summary, [f"{o.id}: {o.reason}" for o in stray])
    summary = (
        f"Every failing test ({len(failures)}) fails to load, "
        "in a file pinned to a changed boundary."
    )
    return _finding("confined", Status.PASS, summary)


def preserved(evidence: Evidence) -> Finding:
    if evidence.as_frozen is None:
        summary = "The suite was modified, so its results are not evidence."
        return _finding("preserved", Status.SKIPPED, summary)
    if evidence.rebound is None:
        summary = "There is no authorised rename to replay through."
        return _finding("preserved", Status.SKIPPED, summary)
    total = len(evidence.rebound.outcomes)
    failures = evidence.rebound.failures()
    if evidence.rebound.all_passed():
        summary = f"All {total} frozen tests pass against the successor."
        return _finding("preserved", Status.PASS, summary)
    details = [f"{o.id}: {o.reason}" for o in failures]
    details += [f"could not bind {error}" for error in evidence.rebound.binding_errors]
    summary = f"Frozen tests failing against the successor: {len(failures)} of {total}."
    return _finding("preserved", Status.FAIL, summary, details)


def _finding(check: str, status: Status, summary: str, details=()) -> Finding:
    return Finding(check, QUESTIONS[check], status, summary, tuple(details))
