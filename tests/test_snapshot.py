"""The snapshot: what is recorded at the freeze and how drift is noticed."""

from __future__ import annotations

from tests.support import MINI_LAYOUT, FrozenProjectTestCase
from verifier.hashing import file_digest
from verifier.log import Scope
from verifier.snapshot import Snapshot, SnapshotIntegrityError, freeze, suite_drift


class FreezeTests(FrozenProjectTestCase):
    def test_it_records_the_public_interface(self):
        self.assertEqual(
            set(self.snapshot.topology.symbols),
            {"app.maths.double", "app.maths.triple", "app.report.summary"},
        )
        self.assertEqual(self.snapshot.topology.imports["app.report"], ("app.maths.double",))

    def test_it_records_the_bytes_and_tests_of_every_suite_file(self):
        frozen = {file.path: file for file in self.snapshot.suite}
        self.assertEqual(
            set(frozen), {"tests/__init__.py", "tests/test_maths.py", "tests/test_report.py"}
        )
        maths = frozen["tests/test_maths.py"]
        self.assertEqual(maths.sha256, file_digest(self.project / "tests/test_maths.py"))
        self.assertEqual(
            maths.tests, ("DoubleTests.test_doubles_a_number", "DoubleTests.test_doubles_zero")
        )
        self.assertEqual(self.snapshot.test_count(), 3)

    def test_it_pins_each_file_to_the_interfaces_it_imports(self):
        frozen = {file.path: file for file in self.snapshot.suite}
        self.assertEqual(frozen["tests/test_maths.py"].pins, ("app.maths.double",))
        self.assertEqual(self.snapshot.boundaries(), ("app.maths.double", "app.report.summary"))

    def test_only_imported_interfaces_are_boundaries(self):
        self.assertTrue(self.snapshot.is_boundary("app.maths.double"))
        self.assertFalse(self.snapshot.is_boundary("app.maths.triple"))

    def test_importing_a_module_pins_everything_in_it(self):
        self.edit("tests/test_maths.py", "from app.maths import double", "import app.maths")
        snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        self.assertTrue(snapshot.is_boundary("app.maths.triple"))

    def test_it_anchors_to_the_log_as_it_stood(self):
        self.log.append("orchestrator", "earlier work", Scope())
        snapshot = freeze(self.project, MINI_LAYOUT, self.log)
        self.assertEqual(snapshot.log_anchor, self.log.head())
        self.assertEqual(snapshot.log_anchor.seq, 1)

    def test_the_id_changes_with_the_content(self):
        self.edit("app/maths.py", "def triple(value):", "def triple(value, times=3):")
        self.assertNotEqual(freeze(self.project, MINI_LAYOUT, self.log).id, self.snapshot.id)


class StorageTests(FrozenProjectTestCase):
    def test_a_saved_snapshot_loads_back_identical(self):
        path = self.scratch / "records" / "snapshot.json"
        self.snapshot.save(path)
        loaded = Snapshot.load(path)
        self.assertEqual(loaded, self.snapshot)
        self.assertEqual(loaded.id, self.snapshot.id)

    def test_an_altered_snapshot_file_is_rejected(self):
        path = self.scratch / "records" / "snapshot.json"
        self.snapshot.save(path)
        path.write_text(path.read_text().replace("app.maths.double", "app.maths.twice"))
        with self.assertRaises(SnapshotIntegrityError):
            Snapshot.load(path)


class SuiteDriftTests(FrozenProjectTestCase):
    def drift(self):
        return suite_drift(self.project, "tests", self.snapshot.suite)

    def test_an_untouched_suite_has_no_drift(self):
        self.assertEqual(self.drift(), ())

    def test_a_modified_test_file_is_reported(self):
        self.edit("tests/test_maths.py", "double(4), 8", "double(4), 9")
        self.assertEqual(self.drift(), ("tests/test_maths.py was modified after the freeze",))

    def test_an_added_file_is_reported(self):
        (self.project / "tests" / "conftest.py").write_text("")
        self.assertEqual(self.drift(), ("tests/conftest.py was added to the frozen suite",))

    def test_a_removed_file_is_reported(self):
        (self.project / "tests" / "test_report.py").unlink()
        self.assertEqual(self.drift(), ("tests/test_report.py was removed from the frozen suite",))
