"""Render a decision as a short, readable trace in Markdown.

The trace has three parts: what the gate saw, how each condition came out,
and the verdict with its consequences. Everything is derived from the
decision object, so a trace cannot say more than the gate actually knew.
"""

from __future__ import annotations

from verifier.gate import Decision
from verifier.trace import observations, outcome


def render(decision: Decision) -> str:
    evidence = decision.evidence
    blocks = [
        "### What the gate saw",
        observations.snapshot(evidence),
        observations.log(evidence),
        observations.delta(evidence),
        observations.suite(evidence),
        "### Conditions",
        outcome.conditions(decision),
        f"### Verdict: `{decision.verdict.value}`",
        decision.headline,
        outcome.consequences(decision),
        outcome.scope_request(decision),
    ]
    return "\n\n".join(block for block in blocks if block) + "\n"


__all__ = ["render"]
