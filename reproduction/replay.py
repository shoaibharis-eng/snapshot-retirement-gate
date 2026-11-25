"""Replay a scenario against a fresh copy of the toy project."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from reproduction.scenarios import ApplyRepair, Evaluate, Instruct, Scenario, Step
from verifier.gate import Decision, Verdict, evaluate
from verifier.hashing import short
from verifier.log import InstructionLog
from verifier.snapshot import Layout, Snapshot, freeze

BASELINE = Path(__file__).parent / "project"
LAYOUT = Layout(packages=("shop",), tests_dir="tests")


@dataclass(frozen=True)
class Event:
    """One step of a replay, as it will appear in the trace."""

    text: str
    decision: Decision | None = None
    expected: Verdict | None = None


@dataclass(frozen=True)
class ScenarioRun:
    scenario: Scenario
    events: tuple[Event, ...]

    def evaluations(self) -> tuple[Event, ...]:
        return tuple(event for event in self.events if event.decision is not None)

    def verdicts(self) -> tuple[Verdict, ...]:
        return tuple(event.decision.verdict for event in self.evaluations())

    def as_expected(self) -> bool:
        return all(event.decision.verdict is event.expected for event in self.evaluations())


def replay(scenario: Scenario, workdir: Path) -> ScenarioRun:
    """Freeze the baseline in ``workdir``, then perform the scenario's steps.

    The project copy and the verifier's records live in sibling directories,
    which keeps the log and the snapshot apart from the code and the suite.
    """
    project = workdir / "project"
    records = workdir / "verifier-records"
    shutil.copytree(BASELINE, project, ignore=shutil.ignore_patterns("__pycache__"))
    log = InstructionLog(records / "instructions.jsonl")
    freeze(project, LAYOUT, log).save(records / "snapshot.json")

    snapshot = Snapshot.load(records / "snapshot.json")
    events = [Event(f"Suite frozen as snapshot `{short(snapshot.id)}`.")]
    events += [_perform(step, project, snapshot, log) for step in scenario.steps]
    return ScenarioRun(scenario, tuple(events))


def replay_in_scratch(scenario: Scenario) -> ScenarioRun:
    with tempfile.TemporaryDirectory(prefix="retirement-gate-") as scratch:
        return replay(scenario, Path(scratch))


def _perform(step: Step, project: Path, snapshot: Snapshot, log: InstructionLog) -> Event:
    if isinstance(step, Instruct):
        entry = log.append(step.issued_by, step.instruction, step.scope)
        return Event(
            f"Instruction logged as entry #{entry.seq} by `{entry.issued_by}`: "
            f'"{entry.instruction}" Scope: {entry.scope.describe()}.'
        )
    if isinstance(step, ApplyRepair):
        step.repair.apply(project)
        return Event(
            f'Repair applied. The agent\'s own account, not used as evidence: "{step.repair.claim}"'
        )
    if isinstance(step, Evaluate):
        decision = evaluate(project, snapshot, log)
        return Event(f"Gate evaluated: `{decision.verdict.value}`.", decision, step.expect)
    raise TypeError(f"unknown step: {step!r}")
