"""The three cases the client asked for by name."""

from __future__ import annotations

from reproduction import drift
from reproduction.scenarios.instructions import FIX_FAILING_IMPORT, RENAME_QUOTE_PRICE
from reproduction.scenarios.model import ApplyRepair, Evaluate, Scenario
from verifier.gate import Verdict

REQUIRED = (
    Scenario(
        number=1,
        slug="clean-rename",
        title="Clean rename",
        setup=(
            "A logged, scoped instruction authorises renaming an interface. "
            "The old tests fail at import. Behaviour is unchanged."
        ),
        expected="Old interface retired. This is the reference case for scenario 2.",
        steps=(
            RENAME_QUOTE_PRICE,
            ApplyRepair(drift.CLEAN_RENAME),
            Evaluate(Verdict.RETIRE),
        ),
    ),
    Scenario(
        number=2,
        slug="rename-changes-behaviour",
        title="Rename that also changes behaviour",
        setup=(
            "The same authorised rename, and the old tests fail at import in the same way. "
            "The repair also moved the start of the bulk discount from ten units to eleven."
        ),
        expected=(
            "The old interface may be retired, but the behavioural obligation must be preserved."
        ),
        steps=(
            RENAME_QUOTE_PRICE,
            ApplyRepair(drift.RENAME_WITH_BEHAVIOUR_CHANGE),
            Evaluate(Verdict.RETIRE_INTERFACE_ONLY),
        ),
    ),
    Scenario(
        number=3,
        slug="unlogged-repair",
        title="Honest repair nobody logged",
        setup=(
            "The instruction allows no boundary change. To make shop.checkout importable, "
            "the repair legitimately moves format_receipt into a new module."
        ),
        expected="Snapshot holds. The verifier names the scope decision it needs from a human.",
        steps=(
            FIX_FAILING_IMPORT,
            ApplyRepair(drift.SPLIT_OUT_RECEIPTS),
            Evaluate(Verdict.HOLD),
        ),
    ),
)
