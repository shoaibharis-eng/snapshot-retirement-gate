"""Shared fixtures: a scratch directory and a miniature frozen project."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from collections.abc import Mapping
from pathlib import Path

from verifier.gate import Decision, evaluate
from verifier.log import InstructionLog, Rename, Scope
from verifier.snapshot import Layout, freeze

MINI_LAYOUT = Layout(packages=("app",))

MINI_PROJECT = {
    "app/__init__.py": "",
    "app/maths.py": """
        def double(value):
            return value * 2


        def triple(value):
            return value * 3
    """,
    "app/report.py": """
        from app.maths import double


        def summary(value):
            return f"twice {value} is {double(value)}"
    """,
    "tests/__init__.py": "",
    "tests/test_maths.py": """
        import unittest

        from app.maths import double


        class DoubleTests(unittest.TestCase):
            def test_doubles_a_number(self):
                self.assertEqual(double(4), 8)

            def test_doubles_zero(self):
                self.assertEqual(double(0), 0)
    """,
    "tests/test_report.py": """
        import unittest

        from app.report import summary


        class SummaryTests(unittest.TestCase):
            def test_summary_mentions_the_result(self):
                self.assertEqual(summary(2), "twice 2 is 4")
    """,
}


def write_files(root: Path, files: Mapping[str, str]) -> Path:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    return root


class ScratchTestCase(unittest.TestCase):
    """Gives each test an empty directory that is removed afterwards."""

    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)


class FrozenProjectTestCase(ScratchTestCase):
    """The miniature project, frozen, with an empty instruction log."""

    def setUp(self) -> None:
        super().setUp()
        self.project = write_files(self.scratch / "project", MINI_PROJECT)
        self.log = InstructionLog(self.scratch / "records" / "instructions.jsonl")
        self.snapshot = freeze(self.project, MINI_LAYOUT, self.log)

    def edit(self, relative: str, old: str, new: str) -> None:
        path = self.project / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def authorise(self, old: str, new: str) -> None:
        self.log.append("orchestrator", f"Rename {old} to {new}.", Scope((Rename(old, new),)))

    def rename_double_everywhere(self) -> None:
        """Rename ``double`` to ``twice`` in the code, leaving the suite alone."""
        self.edit("app/maths.py", "def double(", "def twice(")
        self.edit("app/report.py", "import double", "import twice")
        self.edit("app/report.py", "{double(value)}", "{twice(value)}")

    def decide(self) -> Decision:
        return evaluate(self.project, self.snapshot, self.log)
