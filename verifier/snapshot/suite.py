"""The frozen suite: its bytes, its tests and the boundaries it is pinned to."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verifier.hashing import file_digest
from verifier.snapshot.extract import module_name
from verifier.snapshot.imports import internal_imports


@dataclass(frozen=True)
class FrozenFile:
    """One file of the suite as it was when the suite was frozen."""

    path: str
    sha256: str
    tests: tuple[str, ...]
    pins: tuple[str, ...]

    def is_pinned_to(self, symbol: str) -> bool:
        """True when this file imports ``symbol`` or the module containing it."""
        return any(symbol == pin or symbol.startswith(pin + ".") for pin in self.pins)

    def to_json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "tests": list(self.tests),
            "pins": list(self.pins),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FrozenFile:
        return cls(data["path"], data["sha256"], tuple(data["tests"]), tuple(data["pins"]))


def describe_suite(root: Path, tests_dir: str, packages: Sequence[str]) -> tuple[FrozenFile, ...]:
    """Record every Python file of the suite: hash, test ids and pins."""
    frozen = []
    for path in _suite_files(root, tests_dir):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        is_package = path.name == "__init__.py"
        frozen.append(
            FrozenFile(
                path=path.relative_to(root).as_posix(),
                sha256=file_digest(path),
                tests=_test_ids(tree),
                pins=internal_imports(tree, module_name(root, path), is_package, packages),
            )
        )
    return tuple(frozen)


def suite_drift(root: Path, tests_dir: str, frozen: Sequence[FrozenFile]) -> tuple[str, ...]:
    """Every way the suite on disk differs from the frozen record."""
    recorded = {file.path: file.sha256 for file in frozen}
    current = {
        path.relative_to(root).as_posix(): file_digest(path)
        for path in _suite_files(root, tests_dir)
    }
    problems = []
    for path in sorted(recorded.keys() | current.keys()):
        if path not in current:
            problems.append(f"{path} was removed from the frozen suite")
        elif path not in recorded:
            problems.append(f"{path} was added to the frozen suite")
        elif current[path] != recorded[path]:
            problems.append(f"{path} was modified after the freeze")
    return tuple(problems)


def _suite_files(root: Path, tests_dir: str) -> list[Path]:
    return sorted((root / tests_dir).rglob("*.py"))


def _test_ids(tree: ast.Module) -> tuple[str, ...]:
    """``Class.method`` for every unittest-style test method in the file."""
    return tuple(
        f"{node.name}.{member.name}"
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        for member in node.body
        if isinstance(member, ast.FunctionDef) and member.name.startswith("test")
    )
