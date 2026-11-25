"""The gate when the snapshot must hold, one reason at a time."""

from __future__ import annotations

from tests.support import MINI_LAYOUT, FrozenProjectTestCase
from verifier.gate import Decision, Status, Verdict, evaluate
from verifier.log import Rename, Scope
from verifier.snapshot import freeze
from verifier.suite import FAIL, PASS, Outcome, SuiteRun


class HoldTests(FrozenProjectTestCase):
    def assert_holds(self, decision: Decision, failing: str) -> None:
        self.assertIs(decision.verdict, Verdict.HOLD)
        self.assertEqual(decision.retired, ())
        self.assertEqual(decision.carried, ())
        statuses = {finding.check: finding.status for finding in decision.findings}
        self.assertIs(statuses[failing], Status.FAIL, statuses)

    def test_nothing_changed_so_nothing_is_retired(self):
        decision = self.decide()
        self.assertIs(decision.verdict, Verdict.HOLD)
        self.assertIn("No boundary change is pending", decision.headline)
        self.assertIsNone(decision.scope_request)

    def test_a_plain_bug_is_the_implementation_being_wrong(self):
        self.edit("app/maths.py", "return value * 2", "return value * 2 + 1")
        self.assert_holds(self.decide(), failing="confined")

    def test_an_unlogged_boundary_change_holds_and_asks_a_human(self):
        self.rename_double_everywhere()
        decision = self.decide()
        self.assert_holds(decision, failing="authorised")
        request = decision.scope_request
        self.assertEqual(request.boundaries, ("app.maths.double",))
        self.assertEqual(request.suggested, (Rename("app.maths.double", "app.maths.twice"),))

    def test_an_instruction_without_boundary_scope_authorises_no_boundary_change(self):
        self.log.append("orchestrator", "Fix the failing import.", Scope())
        self.rename_double_everywhere()
        self.assert_holds(self.decide(), failing="authorised")

    def test_an_entry_from_before_the_freeze_cannot_retire_the_snapshot(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        self.rename_double_everywhere()
        self.assert_holds(self.decide(), failing="authorised")

    def test_a_change_outside_the_scope_holds_everything(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/maths.py", "def triple(value):", "def triple(value, times=3):")
        decision = self.decide()
        self.assert_holds(decision, failing="contained")
        self.assertEqual(decision.scope_request.suggested, ())

    def test_a_rename_that_changes_the_signature_holds(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/maths.py", "def twice(value):", "def twice(value, factor=2):")
        self.assert_holds(self.decide(), failing="contained")

    def test_a_failure_away_from_the_boundary_holds(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/report.py", "twice {value} is", "two times {value} is")  # unrelated break
        decision = self.decide()
        self.assert_holds(decision, failing="confined")
        self.assertIn("tests/test_report.py", decision.findings[3].details[0])

    def test_a_forgotten_importer_holds_even_if_no_test_reaches_it(self):
        (self.project / "tests" / "test_report.py").unlink()
        self.snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        self.authorise("app.maths.double", "app.maths.twice")
        self.edit("app/maths.py", "def double(", "def twice(")  # app.report is left behind
        decision = self.decide()
        self.assert_holds(decision, failing="contained")
        self.assertIs(decision.findings[3].status, Status.PASS)  # no test noticed
        self.assertIn("app.report still imports app.maths.double", decision.findings[2].details[0])
        self.assertIsNone(decision.scope_request)  # a defect to fix, not a scope to decide

    def test_an_edited_suite_holds_and_is_not_run(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("tests/test_maths.py", "import double", "import twice as double")
        decision = self.decide()
        self.assert_holds(decision, failing="integrity")
        self.assertIsNone(decision.evidence.as_frozen)
        self.assertIsNone(decision.evidence.rebound)

    def test_a_tampered_log_authorises_nothing(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.log.path.write_text(self.log.path.read_text().replace("orchestrator", "someone"))
        decision = self.decide()
        self.assert_holds(decision, failing="integrity")
        statuses = {finding.check: finding.status for finding in decision.findings}
        self.assertIs(statuses["authorised"], Status.SKIPPED)
        self.assertIsNone(decision.scope_request)


class InjectedSuiteTests(FrozenProjectTestCase):
    """The judgement depends only on the evidence, so the runner can be faked."""

    def test_a_behavioural_failure_in_a_pinned_file_is_not_a_boundary_failure(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()

        def flaky_runner(project, suite, bindings=None):
            outcomes = [
                Outcome(file.path, test, FAIL if "maths" in file.path else PASS, "TimeoutError")
                for file in suite
                for test in file.tests
            ]
            return SuiteRun(tuple(outcomes))

        decision = evaluate(self.project, self.snapshot, self.log, run_suite=flaky_runner)
        self.assertIs(decision.verdict, Verdict.HOLD)
        self.assertIs(decision.findings[3].status, Status.FAIL)
