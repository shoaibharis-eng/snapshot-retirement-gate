"""The required scenarios and the controls, replayed end to end."""

from __future__ import annotations

import functools
import unittest
from pathlib import Path

from reproduction.replay import BASELINE, LAYOUT, ScenarioRun, replay, replay_in_scratch
from reproduction.scenarios import SCENARIOS, find
from tests.support import ScratchTestCase
from verifier.gate import Decision, Status, Verdict
from verifier.log import InstructionLog, Rename
from verifier.snapshot import freeze
from verifier.suite import run_frozen_suite


@functools.cache
def run_of(slug: str) -> ScenarioRun:
    return replay_in_scratch(find(slug))


def decision_of(slug: str) -> Decision:
    return run_of(slug).evaluations()[-1].decision


def statuses(decision: Decision) -> dict[str, Status]:
    return {finding.check: finding.status for finding in decision.findings}


class EveryScenarioTests(unittest.TestCase):
    def test_each_scenario_reaches_its_expected_verdict(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.slug):
                run = run_of(scenario.slug)
                self.assertTrue(run.evaluations())
                self.assertTrue(run.as_expected(), run.verdicts())

    def test_scenarios_are_numbered_in_order(self):
        self.assertEqual([scenario.number for scenario in SCENARIOS], list(range(1, 8)))


class CleanRenameVersusBehaviourChangeTests(unittest.TestCase):
    """Scenarios 1 and 2: what the failures cannot tell apart, and what can."""

    def setUp(self) -> None:
        self.clean = decision_of("clean-rename")
        self.changed = decision_of("rename-changes-behaviour")

    def test_the_frozen_suite_fails_identically_in_both(self):
        self.assertEqual(self.clean.evidence.as_frozen, self.changed.evidence.as_frozen)
        self.assertEqual(self.clean.evidence.delta, self.changed.evidence.delta)

    def test_the_three_agreed_conditions_pass_in_both(self):
        for decision in (self.clean, self.changed):
            found = statuses(decision)
            for check in ("integrity", "authorised", "contained", "confined"):
                self.assertIs(found[check], Status.PASS, check)

    def test_replaying_through_the_log_separates_them(self):
        self.assertIs(statuses(self.clean)["preserved"], Status.PASS)
        self.assertIs(statuses(self.changed)["preserved"], Status.FAIL)
        self.assertEqual(self.clean.evidence.rewritten, ())
        self.assertEqual(self.changed.evidence.rewritten, ("shop.pricing.quote_price",))

    def test_both_retire_the_name_but_only_one_is_clean(self):
        self.assertIs(self.clean.verdict, Verdict.RETIRE)
        self.assertIs(self.changed.verdict, Verdict.RETIRE_INTERFACE_ONLY)
        self.assertEqual(self.clean.retired, self.changed.retired)
        self.assertEqual(len(self.changed.carried), 5)

    def test_the_changed_behaviour_is_named(self):
        violated = [outcome.id for outcome in self.changed.violated]
        expected = "tests/test_pricing.py::QuotePriceTests.test_bulk_discount_starts_at_ten_units"
        self.assertEqual(violated, [expected])


class UnloggedRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = decision_of("unlogged-repair")

    def test_the_snapshot_holds(self):
        self.assertIs(self.decision.verdict, Verdict.HOLD)
        self.assertIs(statuses(self.decision)["authorised"], Status.FAIL)

    def test_the_gate_names_the_scope_decision_it_needs(self):
        request = self.decision.scope_request
        self.assertEqual(request.boundaries, ("shop.checkout.format_receipt",))
        self.assertEqual(
            request.suggested,
            (Rename("shop.checkout.format_receipt", "shop.receipts.format_receipt"),),
        )

    def test_the_failures_alone_look_like_an_honest_repair(self):
        self.assertIs(statuses(self.decision)["confined"], Status.PASS)

    def test_a_human_answer_turns_the_hold_into_a_retirement(self):
        self.assertEqual(run_of("human-ratifies").verdicts(), (Verdict.HOLD, Verdict.RETIRE))


class ControlTests(unittest.TestCase):
    def test_each_control_breaks_exactly_one_gate_condition(self):
        expected = {
            "scope-overreach": "contained",
            "collateral-failure": "confined",
            "suite-edited": "integrity",
        }
        for slug, check in expected.items():
            with self.subTest(scenario=slug):
                found = statuses(decision_of(slug))
                del found["preserved"]  # judged only after the first four pass
                failed = [name for name, status in found.items() if status is Status.FAIL]
                self.assertEqual(failed, [check])


class ReproductionProjectTests(ScratchTestCase):
    def test_the_baseline_suite_is_green_when_frozen(self):
        snapshot = freeze(BASELINE, LAYOUT, InstructionLog(self.scratch / "log.jsonl"))
        self.assertTrue(run_frozen_suite(BASELINE, snapshot.suite).all_passed())
        self.assertEqual(snapshot.test_count(), 9)

    def test_replays_leave_the_frozen_tests_byte_identical(self):
        for scenario in SCENARIOS:
            if scenario.slug == "suite-edited":
                continue  # that control exists to edit the suite
            with self.subTest(scenario=scenario.slug):
                workdir = self.scratch / scenario.slug
                replay(scenario, workdir)
                self.assertEqual(_tests(workdir / "project"), _tests(BASELINE))


def _tests(project: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((project / "tests").glob("*.py"))}
