"""The retirement gate: turn evidence into a verdict.

Rules, in order:

1. If integrity or any of the three agreed conditions does not pass, the
   snapshot holds.
2. If they pass but no authorised rename was carried out, there is nothing to
   retire and the snapshot holds.
3. Otherwise the old interface is retired. Its tests are not: they carry over
   to the successor. If they pass there, the retirement is clean. If they
   fail, the behavioural obligation is preserved and the implementation is
   what is wrong.

The gate never creates or rewrites a test. It only decides which name a
frozen test is bound to.
"""

from __future__ import annotations

from pathlib import Path

from verifier.gate.checks import run_checks
from verifier.gate.decision import Decision, RetiredBoundary, Status, Verdict
from verifier.gate.evidence import Evidence, SuiteRunner, collect
from verifier.gate.scope_request import build_scope_request
from verifier.log import InstructionLog
from verifier.snapshot import Snapshot
from verifier.suite import run_frozen_suite


def evaluate(
    project: Path,
    snapshot: Snapshot,
    log: InstructionLog,
    run_suite: SuiteRunner = run_frozen_suite,
) -> Decision:
    """Observe the project and decide what, if anything, may be retired."""
    return judge(collect(project, snapshot, log, run_suite))


def judge(evidence: Evidence) -> Decision:
    findings = run_checks(evidence)
    *conditions, preserved = findings
    blockers = [finding for finding in conditions if not finding.passed]
    renames = evidence.provenance.exercised

    if blockers:
        verdict, headline = Verdict.HOLD, f"Snapshot holds. {blockers[0].summary}"
    elif not renames:
        verdict, headline = Verdict.HOLD, "Snapshot holds. No boundary change is pending."
    elif preserved.passed:
        verdict = Verdict.RETIRE
        headline = "Old interface retired. Every frozen test passes against its successor."
    elif preserved.status is Status.FAIL:
        verdict = Verdict.RETIRE_INTERFACE_ONLY
        headline = (
            "Old interface retired, behavioural obligation preserved. "
            "The implementation fails frozen tests under the new name, so the "
            "implementation is wrong, not the suite."
        )
    else:
        verdict, headline = Verdict.HOLD, f"Snapshot holds. {preserved.summary}"

    retiring = verdict is not Verdict.HOLD
    retired = tuple(RetiredBoundary(r.old, r.new, r.entry_seq) for r in renames)
    return Decision(
        verdict=verdict,
        headline=headline,
        findings=findings,
        retired=retired if retiring else (),
        carried=_carried_tests(evidence) if retiring else (),
        violated=evidence.rebound.failures() if verdict is Verdict.RETIRE_INTERFACE_ONLY else (),
        caveats=_caveats(evidence) if verdict is Verdict.RETIRE else (),
        scope_request=build_scope_request(evidence) if verdict is Verdict.HOLD else None,
        evidence=evidence,
    )


def _carried_tests(evidence: Evidence) -> tuple[str, ...]:
    """Frozen tests in files pinned to a retired name."""
    retired = [rename.old for rename in evidence.provenance.exercised]
    return tuple(
        f"{file.path}::{test}"
        for file in evidence.snapshot.suite
        if any(file.is_pinned_to(name) for name in retired)
        for test in file.tests
    )


def _caveats(evidence: Evidence) -> tuple[str, ...]:
    bindings = evidence.provenance.bindings()
    return tuple(
        f"The body of {bindings[old]} is not the body {old} had at the freeze. "
        "Every frozen test still passes, but behaviour that no frozen test "
        "asserts is unverified."
        for old in evidence.rewritten
    )
