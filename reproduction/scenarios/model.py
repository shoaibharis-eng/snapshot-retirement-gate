"""What a scenario is: a list of steps replayed against a fresh project copy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from reproduction.repairs import Repair
from verifier.gate import Verdict
from verifier.log import Scope


@dataclass(frozen=True)
class Instruct:
    """Append an instruction, with its scope, to the log."""

    issued_by: str
    instruction: str
    scope: Scope


@dataclass(frozen=True)
class ApplyRepair:
    """Let one scripted repair change the project."""

    repair: Repair


@dataclass(frozen=True)
class Evaluate:
    """Ask the gate for a decision and state the verdict we expect."""

    expect: Verdict


Step = Union[Instruct, ApplyRepair, Evaluate]


@dataclass(frozen=True)
class Scenario:
    number: int
    slug: str
    title: str
    setup: str
    expected: str
    steps: tuple[Step, ...]
