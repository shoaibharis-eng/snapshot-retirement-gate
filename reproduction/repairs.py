"""Scripted repairs: small, replayable edits that stand in for a repair agent.

Each edit fails loudly if the text it expects is missing, so a scenario can
never silently stop reproducing the drift it claims to reproduce.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union


class RepairError(Exception):
    """Raised when a scripted edit no longer applies to the baseline."""


@dataclass(frozen=True)
class RenameSymbol:
    """Rename an identifier in the listed files."""

    old: str
    new: str
    paths: tuple[str, ...]

    def apply(self, project: Path) -> None:
        pattern = re.compile(rf"\b{re.escape(self.old)}\b")
        for relative in self.paths:
            path = project / relative
            text, count = pattern.subn(self.new, path.read_text(encoding="utf-8"))
            if not count:
                raise RepairError(f"{relative} does not mention {self.old}")
            path.write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class ReplaceText:
    """Replace one exact snippet in one file."""

    path: str
    old: str
    new: str

    def apply(self, project: Path) -> None:
        path = project / self.path
        text = path.read_text(encoding="utf-8")
        if text.count(self.old) != 1:
            raise RepairError(f"{self.path} should contain {self.old!r} exactly once")
        path.write_text(text.replace(self.old, self.new), encoding="utf-8")


@dataclass(frozen=True)
class MoveFunction:
    """Cut a top-level function out of one module and start a new module with it."""

    source: str
    name: str
    destination: str
    header: str
    """The docstring and imports of the new module."""

    def apply(self, project: Path) -> None:
        source = project / self.source
        text = source.read_text(encoding="utf-8")
        functions = (n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef))
        node = next((n for n in functions if n.name == self.name), None)
        if node is None:
            raise RepairError(f"{self.source} does not define {self.name}")
        lines = text.splitlines(keepends=True)
        function = "".join(lines[node.lineno - 1 : node.end_lineno])
        remainder = "".join(lines[: node.lineno - 1] + lines[node.end_lineno :])
        source.write_text(remainder.rstrip() + "\n", encoding="utf-8")
        (project / self.destination).write_text(
            f"{self.header.rstrip()}\n\n\n{function}", encoding="utf-8"
        )


Edit = Union[RenameSymbol, ReplaceText, MoveFunction]


@dataclass(frozen=True)
class Repair:
    """One cycle of the repair loop."""

    claim: str
    """What the agent says it did. The gate never treats this as evidence."""
    edits: tuple[Edit, ...]

    def apply(self, project: Path) -> None:
        for edit in self.edits:
            edit.apply(project)
