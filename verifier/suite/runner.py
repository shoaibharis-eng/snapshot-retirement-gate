"""Run the frozen suite in a child interpreter and collect per-test outcomes."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from verifier.snapshot import FrozenFile
from verifier.suite.results import FAIL, UNLOADABLE, Outcome, SuiteRun

_CHILD = Path(__file__).with_name("child.py")
_TIMEOUT_SECONDS = 120


class SuiteRunError(Exception):
    """Raised when the child interpreter could not produce a report at all."""


def run_frozen_suite(
    project: Path, suite: Sequence[FrozenFile], bindings: Mapping[str, str] | None = None
) -> SuiteRun:
    """Run every frozen test once.

    ``bindings`` maps retired names to their successors. With no bindings the
    suite runs exactly as frozen. The test ids come from the snapshot, so a
    file that fails to import still accounts for every test it holds.
    """
    files = [frozen for frozen in suite if frozen.tests]
    request = {
        "suite": [frozen.path for frozen in suite],
        "files": [frozen.path for frozen in files],
        "bindings": dict(bindings or {}),
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-B", str(_CHILD), str(project)],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        message = f"the frozen suite did not finish within {_TIMEOUT_SECONDS} seconds"
        raise SuiteRunError(message) from error
    if completed.returncode != 0:
        raise SuiteRunError(completed.stderr.strip()[-2000:])
    report = json.loads(completed.stdout)
    outcomes = [
        outcome for frozen in files for outcome in _outcomes(frozen, report["files"][frozen.path])
    ]
    return SuiteRun(tuple(outcomes), tuple(report["binding_errors"]))


def _outcomes(frozen: FrozenFile, report: dict) -> list[Outcome]:
    if report["load_error"]:
        return [
            Outcome(frozen.path, test, UNLOADABLE, report["load_error"]) for test in frozen.tests
        ]
    outcomes = []
    for test in frozen.tests:
        result = report["tests"].get(test)
        if result is None:
            outcomes.append(Outcome(frozen.path, test, FAIL, "test was not collected"))
        else:
            outcomes.append(Outcome(frozen.path, test, result["status"], result["reason"]))
    return outcomes
