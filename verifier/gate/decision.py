"""The gate's output: findings per condition, a verdict, and what follows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from verifier.gate.evidence import Evidence
from verifier.log import Rename
from verifier.suite import Outcome


class Verdict(Enum):
    RETIRE = "RETIRE"
    """Old interface retired. Its tests carry over to the successor and pass."""

    RETIRE_INTERFACE_ONLY = "RETIRE_INTERFACE_ONLY"
    """Old interface retired, but its tests still bind and the code fails them."""

    HOLD = "HOLD"
    """Nothing is retired. The snapshot stays fully binding."""


class Status(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class Finding:
    """The result of one condition."""

    check: str
    question: str
    status: Status
    summary: str
    details: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status is Status.PASS


@dataclass(frozen=True)
class RetiredBoundary:
    old: str
    successor: str
    entry_seq: int


@dataclass(frozen=True)
class ScopeRequest:
    """The scope decision the gate needs a human to make."""

    boundaries: tuple[str, ...]
    """Interfaces the frozen suite depends on that changed without a scope."""
    suggested: tuple[Rename, ...]
    """A draft scope inferred from the diff. It is a question, not evidence."""


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    headline: str
    findings: tuple[Finding, ...]
    retired: tuple[RetiredBoundary, ...]
    carried: tuple[str, ...]
    """Frozen tests that stay binding, now against the successor interface."""
    violated: tuple[Outcome, ...]
    """Carried tests the current implementation fails."""
    caveats: tuple[str, ...]
    scope_request: ScopeRequest | None
    evidence: Evidence
