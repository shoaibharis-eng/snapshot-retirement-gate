"""Running the frozen suite, as frozen and re-bound through a rename."""

from __future__ import annotations

from tests.support import MINI_LAYOUT, FrozenProjectTestCase
from verifier.snapshot import freeze, suite_drift
from verifier.suite import FAIL, PASS, UNLOADABLE, run_frozen_suite


class AsFrozenTests(FrozenProjectTestCase):
    def run_suite(self, bindings=None):
        return run_frozen_suite(self.project, self.snapshot.suite, bindings)

    def test_a_healthy_project_passes_every_frozen_test(self):
        run = self.run_suite()
        self.assertEqual([outcome.status for outcome in run.outcomes], [PASS, PASS, PASS])
        self.assertTrue(run.all_passed())

    def test_a_failing_assertion_is_reported_with_its_reason(self):
        self.edit("app/maths.py", "return value * 2", "return value * 2 + 1")
        failures = {outcome.id: outcome for outcome in self.run_suite().failures()}
        doubled = failures["tests/test_maths.py::DoubleTests.test_doubles_a_number"]
        self.assertEqual(doubled.status, FAIL)
        self.assertEqual(doubled.reason, "AssertionError: 9 != 8")

    def test_a_file_that_cannot_be_imported_accounts_for_all_its_tests(self):
        self.edit("app/maths.py", "def double(", "def twice(")
        run = self.run_suite()
        unloadable = [outcome for outcome in run.outcomes if outcome.status == UNLOADABLE]
        self.assertEqual(len(unloadable), 3)  # test_report imports app.report, which imports double
        self.assertEqual({outcome.reason for outcome in unloadable}, {"ImportError"})

    def test_what_a_test_prints_does_not_corrupt_the_report(self):
        self.edit("app/maths.py", "return value * 2", "print('noise'); return value * 2")
        self.assertTrue(self.run_suite().all_passed())

    def test_class_level_fixtures_are_run(self):
        self.use_a_class_fixture("cls.zero = 0")
        snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        self.assertTrue(run_frozen_suite(self.project, snapshot.suite).all_passed())

    def test_a_failing_fixture_fails_its_tests(self):
        self.use_a_class_fixture("raise RuntimeError('no database')")
        snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        failures = run_frozen_suite(self.project, snapshot.suite).failures()
        self.assertEqual({outcome.file for outcome in failures}, {"tests/test_maths.py"})
        self.assertEqual(len(failures), 2)

    def use_a_class_fixture(self, body: str) -> None:
        self.edit(
            "tests/test_maths.py",
            "    def test_doubles_zero(self):\n        self.assertEqual(double(0), 0)",
            f"    @classmethod\n    def setUpClass(cls):\n        {body}\n\n"
            "    def test_doubles_zero(self):\n"
            "        self.assertEqual(double(getattr(self, 'zero', 0)), 0)",
        )

    def test_a_skipped_test_does_not_count_as_passing(self):
        skipped = "    @unittest.skip('later')\n    def test_summary"
        self.edit("tests/test_report.py", "    def test_summary", skipped)
        snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        run = run_frozen_suite(self.project, snapshot.suite)
        self.assertEqual([outcome.reason for outcome in run.failures()], ["skipped"])


class RebindingTests(FrozenProjectTestCase):
    BINDING = {"app.maths.double": "app.maths.twice"}

    def run_suite(self, bindings=None):
        return run_frozen_suite(self.project, self.snapshot.suite, bindings)

    def test_a_binding_lets_frozen_tests_reach_the_renamed_interface(self):
        self.rename_double_everywhere()
        self.assertFalse(self.run_suite().all_passed())
        self.assertTrue(self.run_suite(self.BINDING).all_passed())

    def test_re_bound_tests_still_judge_the_behaviour(self):
        self.rename_double_everywhere()
        self.edit("app/maths.py", "return value * 2", "return value * 2 + 1")
        failures = self.run_suite(self.BINDING).failures()
        self.assertIn(
            "tests/test_maths.py::DoubleTests.test_doubles_a_number",
            [outcome.id for outcome in failures],
        )

    def test_a_binding_is_served_to_the_suite_but_not_to_the_implementation(self):
        self.edit("app/maths.py", "def double(", "def twice(")  # app.report still imports double
        run = self.run_suite(self.BINDING)
        by_file = {outcome.file: outcome.status for outcome in run.outcomes}
        self.assertEqual(by_file["tests/test_maths.py"], PASS)
        self.assertEqual(by_file["tests/test_report.py"], UNLOADABLE)

    def test_a_binding_works_when_the_old_module_is_gone(self):
        (self.project / "app" / "maths.py").rename(self.project / "app" / "numbers.py")
        self.edit("app/report.py", "from app.maths import double", "from app.numbers import double")
        run = self.run_suite({"app.maths.double": "app.numbers.double"})
        self.assertTrue(run.all_passed())

    def test_a_binding_that_cannot_be_made_is_reported(self):
        run = self.run_suite({"app.maths.gone": "app.maths.missing"})
        self.assertEqual(
            run.binding_errors, ("app.maths.gone -> app.maths.missing: AttributeError",)
        )
        self.assertFalse(run.all_passed())

    def test_running_the_suite_never_touches_the_project(self):
        self.rename_double_everywhere()
        before = {path: path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.run_suite(self.BINDING)
        after = {path: path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(suite_drift(self.project, "tests", self.snapshot.suite), ())
