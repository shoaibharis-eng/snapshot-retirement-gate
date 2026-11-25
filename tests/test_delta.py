"""The interface delta between the snapshot and the repaired project."""

from __future__ import annotations

from tests.support import FrozenProjectTestCase
from verifier.gate import Change, ChangeKind, interface_delta
from verifier.snapshot import extract_topology


class InterfaceDeltaTests(FrozenProjectTestCase):
    def delta(self) -> tuple[Change, ...]:
        observed = extract_topology(self.project, self.snapshot.layout.packages)
        return interface_delta(self.snapshot.topology, observed)

    def test_an_unchanged_project_has_no_delta(self):
        self.assertEqual(self.delta(), ())

    def test_an_implementation_change_is_not_an_interface_change(self):
        self.edit("app/maths.py", "return value * 2", "return value + value")
        self.assertEqual(self.delta(), ())

    def test_a_rename_is_a_removal_an_addition_and_rewired_imports(self):
        self.rename_double_everywhere()
        self.assertEqual(
            self.delta(),
            (
                Change(ChangeKind.SYMBOL_REMOVED, "app.maths.double"),
                Change(ChangeKind.SYMBOL_ADDED, "app.maths.twice"),
                Change(ChangeKind.IMPORT_REMOVED, "app.report", "app.maths.double"),
                Change(ChangeKind.IMPORT_ADDED, "app.report", "app.maths.twice"),
            ),
        )

    def test_a_changed_signature_is_reported_with_both_forms(self):
        self.edit("app/maths.py", "def triple(value):", "def triple(value, times=3):")
        expected = Change(
            ChangeKind.SIGNATURE_CHANGED, "app.maths.triple", "(value) became (value, times=3)"
        )
        self.assertEqual(self.delta(), (expected,))

    def test_a_new_dependency_between_modules_is_reported(self):
        self.edit("app/maths.py", "def double(", "from app.report import summary\n\n\ndef double(")
        self.assertEqual(
            self.delta(), (Change(ChangeKind.IMPORT_ADDED, "app.maths", "app.report.summary"),)
        )

    def test_changes_describe_themselves(self):
        self.rename_double_everywhere()
        described = [change.describe() for change in self.delta()]
        self.assertIn("symbol removed: app.maths.double", described)
        self.assertIn("import added: app.report imports app.maths.twice", described)
