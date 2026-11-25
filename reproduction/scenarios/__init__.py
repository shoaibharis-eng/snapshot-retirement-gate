"""The scenario catalogue: three required cases and four controls."""

from __future__ import annotations

from reproduction.scenarios.controls import CONTROLS
from reproduction.scenarios.model import ApplyRepair, Evaluate, Instruct, Scenario, Step
from reproduction.scenarios.required import REQUIRED

SCENARIOS = REQUIRED + CONTROLS


def find(key: str) -> Scenario:
    """Look a scenario up by number or name."""
    for scenario in SCENARIOS:
        if key in (str(scenario.number), scenario.slug):
            return scenario
    raise KeyError(key)


__all__ = ["SCENARIOS", "ApplyRepair", "Evaluate", "Instruct", "Scenario", "Step", "find"]
