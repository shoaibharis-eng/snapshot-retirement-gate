"""Controls: variations that are not in the brief.

Scenarios 4, 5 and 7 each make exactly one of the gate's first four conditions
fail while the other three pass. Scenario 6 continues scenario 3 to show a hold
turning into a retirement.
"""

from __future__ import annotations

from reproduction import drift
from reproduction.scenarios.instructions import (
    ACCEPT_RECEIPTS_SPLIT,
    FIX_FAILING_IMPORT,
    RENAME_QUOTE_PRICE,
)
from reproduction.scenarios.model import ApplyRepair, Evaluate, Scenario
from verifier.gate import Verdict

CONTROLS = (
    Scenario(
        number=4,
        slug="scope-overreach",
        title="Control: the repair exceeds its scope",
        setup=(
            "The authorised rename, plus a signature change to unit_price that no "
            "entry allows. No frozen test imports unit_price, so no test notices."
        ),
        expected="Snapshot holds: the interface delta is not contained in the scope.",
        steps=(
            RENAME_QUOTE_PRICE,
            ApplyRepair(drift.RENAME_PLUS_SIGNATURE_CHANGE),
            Evaluate(Verdict.HOLD),
        ),
    ),
    Scenario(
        number=5,
        slug="collateral-failure",
        title="Control: failures outside the retired boundary",
        setup=(
            "The authorised rename, done correctly, but the same repair also changed a "
            "catalogue price. Tests that have nothing to do with the rename now fail."
        ),
        expected="Snapshot holds: the suite fails away from the retired boundary.",
        steps=(
            RENAME_QUOTE_PRICE,
            ApplyRepair(drift.RENAME_WITH_COLLATERAL_DAMAGE),
            Evaluate(Verdict.HOLD),
        ),
    ),
    Scenario(
        number=6,
        slug="human-ratifies",
        title="Control: a human answers the scope question",
        setup=(
            "Scenario 3, continued. After the gate holds, a human appends the scope "
            "it asked for, and the gate is asked again."
        ),
        expected="Holds first, then retires once the log covers the change.",
        steps=(
            FIX_FAILING_IMPORT,
            ApplyRepair(drift.SPLIT_OUT_RECEIPTS),
            Evaluate(Verdict.HOLD),
            ACCEPT_RECEIPTS_SPLIT,
            Evaluate(Verdict.RETIRE),
        ),
    ),
    Scenario(
        number=7,
        slug="suite-edited",
        title="Control: the repair edits the frozen suite",
        setup=(
            "The authorised rename, but the repair also rewrites the frozen test's "
            "import so that everything turns green."
        ),
        expected="Snapshot holds: a modified suite is not evidence.",
        steps=(
            RENAME_QUOTE_PRICE,
            ApplyRepair(drift.RENAME_AND_EDIT_THE_SUITE),
            Evaluate(Verdict.HOLD),
        ),
    ),
)
