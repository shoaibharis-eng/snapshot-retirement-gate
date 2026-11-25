"""Evidence: everything the gate observes before it judges anything.

Collecting is kept apart from judging. ``collect`` does all the reading and
running; ``verifier.gate.judge`` is then a pure function of what was seen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from verifier.gate.delta import Change, ChangeKind, interface_delta
from verifier.gate.provenance import Provenance, trace_provenance
from verifier.log import InstructionLog, LogEntry, LogIntegrityError
from verifier.snapshot import Snapshot, Topology, extract_topology, suite_drift
from verifier.suite import SuiteRun, run_frozen_suite

SuiteRunner = Callable[..., SuiteRun]


@dataclass(frozen=True)
class Evidence:
    snapshot: Snapshot
    observed: Topology
    """The project's shape right now."""
    log_problem: str
    """Why the log cannot be trusted, or empty when it is intact."""
    entries: tuple[LogEntry, ...]
    """Entries appended since the freeze. Only these can retire anything."""
    suite_drift: tuple[str, ...]
    delta: tuple[Change, ...]
    provenance: Provenance
    as_frozen: SuiteRun | None
    """The frozen suite run untouched. None if the suite was tampered with."""
    rebound: SuiteRun | None
    """The same suite with retired names bound to their logged successors."""
    rewritten: tuple[str, ...]
    """Renamed symbols whose body is no longer the one in the snapshot."""

    def boundary_changes(self) -> tuple[Change, ...]:
        """Changes that take away or alter an interface the frozen suite uses."""
        breaking = (ChangeKind.SYMBOL_REMOVED, ChangeKind.SIGNATURE_CHANGED)
        return tuple(
            change
            for change in self.delta
            if change.kind in breaking and self.snapshot.is_boundary(change.subject)
        )


def collect(
    project: Path,
    snapshot: Snapshot,
    log: InstructionLog,
    run_suite: SuiteRunner = run_frozen_suite,
) -> Evidence:
    try:
        entries, log_problem = log.entries_after(snapshot.log_anchor), ""
    except LogIntegrityError as error:
        entries, log_problem = (), str(error)

    observed = extract_topology(project, snapshot.layout.packages)
    delta = interface_delta(snapshot.topology, observed)
    provenance = trace_provenance(delta, entries, snapshot.topology, observed)
    drift = suite_drift(project, snapshot.layout.tests_dir, snapshot.suite)

    as_frozen = rebound = None
    if not drift:
        as_frozen = run_suite(project, snapshot.suite)
        if provenance.exercised:
            rebound = run_suite(project, snapshot.suite, provenance.bindings())

    rewritten = tuple(
        rename.old
        for rename in provenance.exercised
        if rename.new in observed.symbols
        and observed.symbols[rename.new].fingerprint
        != snapshot.topology.symbols[rename.old].fingerprint
    )
    return Evidence(
        snapshot=snapshot,
        observed=observed,
        log_problem=log_problem,
        entries=entries,
        suite_drift=drift,
        delta=delta,
        provenance=provenance,
        as_frozen=as_frozen,
        rebound=rebound,
        rewritten=rewritten,
    )
