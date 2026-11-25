"""The gate when retirement is on the table: clean, partial, with a caveat."""

from __future__ import annotations

from tests.support import MINI_LAYOUT, FrozenProjectTestCase, ScratchTestCase, write_files
from verifier.gate import RetiredBoundary, Status, Verdict, evaluate
from verifier.log import InstructionLog, Rename, Scope
from verifier.snapshot import freeze

MATHS_TESTS = (
    "tests/test_maths.py::DoubleTests.test_doubles_a_number",
    "tests/test_maths.py::DoubleTests.test_doubles_zero",
)


class CleanRenameTests(FrozenProjectTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.decision = self.decide()

    def test_the_old_interface_is_retired(self):
        self.assertIs(self.decision.verdict, Verdict.RETIRE)
        self.assertEqual(
            self.decision.retired, (RetiredBoundary("app.maths.double", "app.maths.twice", 1),)
        )

    def test_every_condition_passes(self):
        self.assertEqual({finding.status for finding in self.decision.findings}, {Status.PASS})

    def test_the_frozen_tests_are_carried_forward_not_dropped(self):
        self.assertEqual(self.decision.carried, MATHS_TESTS)
        self.assertEqual(self.decision.violated, ())

    def test_an_unchanged_body_needs_no_caveat(self):
        self.assertEqual(self.decision.caveats, ())
        self.assertEqual(self.decision.evidence.rewritten, ())


class RenameWithBehaviourChangeTests(FrozenProjectTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/maths.py", "return value * 2", "return value * 2 + (value > 3)")
        self.decision = self.decide()

    def test_only_the_interface_is_retired(self):
        self.assertIs(self.decision.verdict, Verdict.RETIRE_INTERFACE_ONLY)
        self.assertEqual(self.decision.retired[0].successor, "app.maths.twice")

    def test_the_three_agreed_conditions_all_pass(self):
        statuses = {finding.check: finding.status for finding in self.decision.findings}
        for check in ("integrity", "authorised", "contained", "confined"):
            self.assertIs(statuses[check], Status.PASS, check)
        self.assertIs(statuses["preserved"], Status.FAIL)

    def test_the_violated_obligation_is_named(self):
        self.assertEqual([outcome.id for outcome in self.decision.violated], [MATHS_TESTS[0]])
        self.assertEqual(self.decision.violated[0].reason, "AssertionError: 9 != 8")

    def test_the_obligations_stay_binding(self):
        self.assertEqual(self.decision.carried, MATHS_TESTS)


class RefactorDuringRenameTests(FrozenProjectTestCase):
    def test_a_rewritten_body_that_still_passes_retires_with_a_caveat(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/maths.py", "return value * 2", "return value + value")
        decision = self.decide()
        self.assertIs(decision.verdict, Verdict.RETIRE)
        self.assertEqual(decision.evidence.rewritten, ("app.maths.double",))
        self.assertIn("behaviour that no frozen test asserts is unverified", decision.caveats[0])


class ChainedRenameTests(FrozenProjectTestCase):
    def test_renames_from_two_entries_compose(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.authorise("app.maths.twice", "app.maths.two_times")
        self.edit("app/maths.py", "def double(", "def two_times(")
        self.edit("app/report.py", "import double", "import two_times")
        self.edit("app/report.py", "{double(value)}", "{two_times(value)}")
        decision = self.decide()
        self.assertIs(decision.verdict, Verdict.RETIRE)
        self.assertEqual(
            decision.retired, (RetiredBoundary("app.maths.double", "app.maths.two_times", 2),)
        )


class NeverRegenerateTests(FrozenProjectTestCase):
    def test_deciding_never_creates_or_rewrites_a_test(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        before = {path: path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.decide()
        after = {path: path.read_bytes() for path in self.project.rglob("*") if path.is_file()}
        self.assertEqual(before, after)


class ForgottenCallerTests(ScratchTestCase):
    """The replay must not hide a caller that still uses the retired name."""

    FILES = {
        "app/__init__.py": "",
        "app/maths.py": "def double(value):\n    return value * 2\n",
        "app/report.py": """
            import app.maths


            def summary(value):
                return app.maths.double(value)
        """,
        "tests/__init__.py": "",
        "tests/test_app.py": """
            import unittest

            from app.maths import double
            from app.report import summary


            class AppTests(unittest.TestCase):
                def test_double(self):
                    self.assertEqual(double(2), 4)

                def test_summary(self):
                    self.assertEqual(summary(2), 4)
        """,
    }

    def test_the_old_name_comes_back_for_the_suite_only(self):
        project = write_files(self.scratch / "project", self.FILES)
        log = InstructionLog(self.scratch / "instructions.jsonl")
        snapshot = freeze(project, MINI_LAYOUT, log)
        log.append(
            "orchestrator",
            "Rename double.",
            Scope((Rename("app.maths.double", "app.maths.twice"),)),
        )
        self.rename_only_the_definition(project)

        decision = evaluate(project, snapshot, log)

        self.assertIs(decision.verdict, Verdict.RETIRE_INTERFACE_ONLY)
        self.assertEqual([outcome.test for outcome in decision.violated], ["AppTests.test_summary"])

    @staticmethod
    def rename_only_the_definition(project) -> None:
        path = project / "app" / "maths.py"
        path.write_text(path.read_text().replace("def double(", "def twice("))
