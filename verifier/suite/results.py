"""What one run of the frozen suite observed."""

from __future__ import annotations

from dataclasses import dataclass

PASS = "pass"
FAIL = "fail"
UNLOADABLE = "unloadable"
"""The test's file could not be imported, so the test never reached the code."""


@dataclass(frozen=True)
class Outcome:
    """The result of one frozen test."""

    file: str
    test: str
    status: str
    reason: str = ""

    @property
    def id(self) -> str:
        return f"{self.file}::{self.test}"


@dataclass(frozen=True)
class SuiteRun:
    outcomes: tuple[Outcome, ...]
    binding_errors: tuple[str, ...] = ()

    def failures(self) -> tuple[Outcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.status != PASS)

    def for_file(self, path: str) -> tuple[Outcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.file == path)

    def all_passed(self) -> bool:
        return not self.failures() and not self.binding_errors
