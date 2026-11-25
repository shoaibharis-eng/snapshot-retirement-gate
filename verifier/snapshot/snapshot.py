"""The snapshot the frozen suite is pinned to.

A snapshot is immutable and identified by the hash of its content. It records
where the instruction log stood at the freeze, so that only entries appended
afterwards can ever count towards retiring it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verifier.hashing import digest
from verifier.log import InstructionLog, LogHead
from verifier.snapshot.extract import extract_topology
from verifier.snapshot.suite import FrozenFile, describe_suite
from verifier.snapshot.topology import Topology


class SnapshotIntegrityError(Exception):
    """Raised when a stored snapshot does not match its own identifier."""


@dataclass(frozen=True)
class Layout:
    """Where the code and the suite live inside the project directory."""

    packages: tuple[str, ...]
    tests_dir: str = "tests"


@dataclass(frozen=True)
class Snapshot:
    layout: Layout
    topology: Topology
    suite: tuple[FrozenFile, ...]
    log_anchor: LogHead

    @property
    def id(self) -> str:
        return digest(self._content())

    def boundaries(self) -> tuple[str, ...]:
        """Every interface the frozen suite depends on."""
        return tuple(sorted({pin for file in self.suite for pin in file.pins}))

    def is_boundary(self, symbol: str) -> bool:
        return any(file.is_pinned_to(symbol) for file in self.suite)

    def test_count(self) -> int:
        return sum(len(file.tests) for file in self.suite)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = {"id": self.id, **self._content()}
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Snapshot:
        document = json.loads(path.read_text(encoding="utf-8"))
        snapshot = cls(
            layout=Layout(tuple(document["layout"]["packages"]), document["layout"]["tests_dir"]),
            topology=Topology.from_json(document["topology"]),
            suite=tuple(FrozenFile.from_json(item) for item in document["suite"]),
            log_anchor=LogHead.from_json(document["log_anchor"]),
        )
        if snapshot.id != document["id"]:
            raise SnapshotIntegrityError(f"{path} does not match its recorded id")
        return snapshot

    def _content(self) -> dict[str, Any]:
        return {
            "layout": {"packages": list(self.layout.packages), "tests_dir": self.layout.tests_dir},
            "topology": self.topology.to_json(),
            "suite": [file.to_json() for file in self.suite],
            "log_anchor": self.log_anchor.to_json(),
        }


def freeze(project: Path, layout: Layout, log: InstructionLog) -> Snapshot:
    """Record the project's shape and the suite's bytes as they are right now."""
    return Snapshot(
        layout=layout,
        topology=extract_topology(project, layout.packages),
        suite=describe_suite(project, layout.tests_dir, layout.packages),
        log_anchor=log.head(),
    )
