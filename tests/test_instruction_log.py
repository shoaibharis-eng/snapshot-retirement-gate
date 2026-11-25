"""The instruction log: append-only, hash-chained, and every entry scoped."""

from __future__ import annotations

from tests.support import ScratchTestCase
from verifier.log import GENESIS, InstructionLog, LogHead, LogIntegrityError, Rename, Scope

RENAME = Scope((Rename("app.maths.double", "app.maths.twice"),))


class AppendTests(ScratchTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.log = InstructionLog(self.scratch / "instructions.jsonl")

    def test_an_empty_log_starts_at_genesis(self):
        self.assertEqual(self.log.entries(), ())
        self.assertEqual(self.log.head(), LogHead(0, GENESIS))

    def test_entries_are_numbered_and_chained(self):
        first = self.log.append("orchestrator", "one", Scope())
        second = self.log.append("orchestrator", "two", RENAME)
        self.assertEqual((first.seq, second.seq), (1, 2))
        self.assertEqual(first.prev_hash, GENESIS)
        self.assertEqual(second.prev_hash, first.entry_hash)
        self.assertEqual(self.log.head(), LogHead(2, second.entry_hash))

    def test_an_entry_records_its_scope(self):
        self.log.append("orchestrator", "rename it", RENAME)
        stored = InstructionLog(self.log.path).entries()[0]
        self.assertEqual(stored.scope, RENAME)
        self.assertEqual(stored.instruction, "rename it")
        self.assertEqual(stored.issued_by, "orchestrator")

    def test_appending_leaves_earlier_bytes_untouched(self):
        self.log.append("orchestrator", "one", Scope())
        before = self.log.path.read_bytes()
        self.log.append("orchestrator", "two", RENAME)
        self.assertTrue(self.log.path.read_bytes().startswith(before))

    def test_entries_after_an_anchor_are_only_the_newer_ones(self):
        self.log.append("orchestrator", "one", Scope())
        anchor = self.log.head()
        newer = self.log.append("orchestrator", "two", RENAME)
        self.assertEqual(self.log.entries_after(anchor), (newer,))


class TamperTests(ScratchTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.log = InstructionLog(self.scratch / "instructions.jsonl")
        self.log.append("orchestrator", "one", Scope())
        self.log.append("orchestrator", "two", Scope())
        self.log.append("orchestrator", "three", Scope())

    def rewrite(self, transform) -> None:
        lines = self.log.path.read_text(encoding="utf-8").splitlines()
        self.log.path.write_text("\n".join(transform(lines)) + "\n", encoding="utf-8")

    def test_editing_an_instruction_is_detected(self):
        self.rewrite(lambda lines: [lines[0], lines[1].replace("two", "2"), lines[2]])
        with self.assertRaisesRegex(LogIntegrityError, "entry #2 was altered"):
            self.log.entries()

    def test_widening_a_scope_after_the_fact_is_detected(self):
        rename = '{"from":"app.maths.double","op":"rename","to":"app.maths.x"}'
        widened = f'"boundary_changes":[{rename}]'
        self.rewrite(lambda lines: [lines[0].replace('"boundary_changes":[]', widened)] + lines[1:])
        with self.assertRaisesRegex(LogIntegrityError, "entry #1 was altered"):
            self.log.entries()

    def test_removing_an_entry_is_detected(self):
        self.rewrite(lambda lines: [lines[0], lines[2]])
        with self.assertRaises(LogIntegrityError):
            self.log.entries()

    def test_reordering_entries_is_detected(self):
        self.rewrite(lambda lines: [lines[1], lines[0], lines[2]])
        with self.assertRaises(LogIntegrityError):
            self.log.entries()

    def test_a_line_that_is_not_an_entry_is_detected(self):
        self.rewrite(lambda lines: lines + ["not json"])
        with self.assertRaisesRegex(LogIntegrityError, "line 4 is not a log entry"):
            self.log.entries()

    def test_truncating_below_an_anchor_is_detected(self):
        anchor = self.log.head()
        self.rewrite(lambda lines: lines[:2])
        with self.assertRaisesRegex(LogIntegrityError, "had 3 at the anchor"):
            self.log.entries_after(anchor)

    def test_a_rewritten_history_does_not_extend_the_anchor(self):
        anchor = self.log.head()
        self.log.path.unlink()
        for text in ("one", "two", "a different third", "four"):
            self.log.append("orchestrator", text, Scope())
        self.assertEqual(len(self.log.entries()), 4)  # a valid chain, but not ours
        with self.assertRaisesRegex(LogIntegrityError, "rewritten before the anchor"):
            self.log.entries_after(anchor)
