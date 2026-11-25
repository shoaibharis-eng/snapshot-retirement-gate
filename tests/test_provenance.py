"""Provenance: tracing each interface change back to a scoped log entry."""

from __future__ import annotations

from tests.support import FrozenProjectTestCase
from verifier.gate import Provenance, interface_delta, net_renames, trace_provenance
from verifier.log import Rename, Scope
from verifier.snapshot import extract_topology


class ProvenanceTests(FrozenProjectTestCase):
    def provenance(self) -> Provenance:
        observed = extract_topology(self.project, self.snapshot.layout.packages)
        delta = interface_delta(self.snapshot.topology, observed)
        entries = self.log.entries_after(self.snapshot.log_anchor)
        return trace_provenance(delta, entries, self.snapshot.topology, observed)

    def test_an_authorised_rename_covers_its_whole_delta(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        provenance = self.provenance()
        self.assertEqual(provenance.uncovered(), ())
        self.assertEqual({a.entry_seq for a in provenance.attributions}, {1})
        self.assertEqual(provenance.bindings(), {"app.maths.double": "app.maths.twice"})

    def test_without_an_entry_nothing_is_covered(self):
        self.rename_double_everywhere()
        provenance = self.provenance()
        self.assertEqual(len(provenance.uncovered()), 4)
        self.assertEqual(provenance.exercised, ())

    def test_an_authorisation_that_was_not_used_changes_nothing(self):
        self.authorise("app.maths.double", "app.maths.twice")
        provenance = self.provenance()
        self.assertEqual(provenance.exercised, ())
        self.assertEqual(provenance.violations, ())

    def test_a_change_beside_the_rename_stays_uncovered(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/report.py", "def summary(value):", "def summary(value, loud=False):")
        uncovered = [change.describe() for change in self.provenance().uncovered()]
        self.assertEqual(
            uncovered, ["signature changed: app.report.summary (value) became (value, loud=False)"]
        )

    def test_a_new_import_in_an_untouched_module_stays_uncovered(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        (self.project / "app" / "extra.py").write_text("from app.report import summary\n")
        uncovered = [change.describe() for change in self.provenance().uncovered()]
        self.assertEqual(uncovered, ["import added: app.extra imports app.report.summary"])

    def test_a_missing_successor_violates_the_scope(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.edit("app/maths.py", "def double(", "def _double(")
        self.assertIn("app.maths.twice does not exist", self.provenance().violations[0])

    def test_a_module_still_importing_the_old_name_violates_the_scope(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.edit("app/maths.py", "def double(", "def twice(")  # app.report is left behind
        self.assertEqual(
            self.provenance().violations,
            ("app.report still imports app.maths.double, which entry #1 renamed away",),
        )

    def test_a_rename_may_not_change_the_signature(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.rename_double_everywhere()
        self.edit("app/maths.py", "def twice(value):", "def twice(value, factor=2):")
        self.assertIn("does not keep the signature", self.provenance().violations[0])

    def test_a_move_to_a_new_module_is_covered_with_its_imports(self):
        self.authorise("app.maths.triple", "app.more.triple")
        self.edit("app/maths.py", "def triple(value):\n    return value * 3\n", "")
        (self.project / "app" / "more.py").write_text(
            "from app.maths import double\n\n\ndef triple(value):\n    return value * 3\n"
        )
        self.assertEqual(self.provenance().uncovered(), ())


class NetRenameTests(FrozenProjectTestCase):
    def net(self):
        return net_renames(self.log.entries())

    def test_chained_renames_net_out_to_the_latest_name(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.authorise("app.maths.twice", "app.maths.two_times")
        self.assertEqual(
            [(r.old, r.new, r.entry_seq) for r in self.net()],
            [("app.maths.double", "app.maths.two_times", 2)],
        )

    def test_renaming_back_cancels_out(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.authorise("app.maths.twice", "app.maths.double")
        self.assertEqual(self.net(), [])

    def test_a_later_entry_about_the_same_name_wins(self):
        self.authorise("app.maths.double", "app.maths.twice")
        self.authorise("app.maths.double", "app.maths.dbl")
        self.assertEqual(
            [(r.old, r.new, r.entry_seq) for r in self.net()],
            [("app.maths.double", "app.maths.dbl", 2)],
        )

    def test_an_entry_can_carry_several_renames(self):
        scope = Scope(
            (
                Rename("app.maths.double", "app.maths.twice"),
                Rename("app.maths.triple", "app.maths.thrice"),
            )
        )
        self.log.append("orchestrator", "rename both", scope)
        self.assertEqual(len(self.net()), 2)
