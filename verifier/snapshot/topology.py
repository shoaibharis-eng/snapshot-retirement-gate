"""The data model for a project's shape.

A topology is two maps. ``symbols`` holds every public symbol under its
qualified name, and ``imports`` holds, for every module, the project-internal
names it imports. Modules are the keys of ``imports``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Symbol:
    """One public symbol.

    ``kind`` and ``signature`` are its interface. ``fingerprint`` hashes its
    body with the name left out, so a pure rename keeps the same fingerprint.
    """

    kind: str
    signature: str
    fingerprint: str

    def interface(self) -> tuple[str, str]:
        return (self.kind, self.signature)

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "signature": self.signature, "fingerprint": self.fingerprint}

    @classmethod
    def from_json(cls, data: dict[str, str]) -> Symbol:
        return cls(data["kind"], data["signature"], data["fingerprint"])


@dataclass(frozen=True)
class Topology:
    symbols: Mapping[str, Symbol]
    imports: Mapping[str, tuple[str, ...]]

    @property
    def modules(self) -> tuple[str, ...]:
        return tuple(sorted(self.imports))

    def to_json(self) -> dict[str, Any]:
        return {
            "symbols": {name: symbol.to_json() for name, symbol in self.symbols.items()},
            "imports": {module: list(targets) for module, targets in self.imports.items()},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Topology:
        return cls(
            symbols={name: Symbol.from_json(item) for name, item in data["symbols"].items()},
            imports={module: tuple(targets) for module, targets in data["imports"].items()},
        )


def module_of(qualified_name: str) -> str:
    """``shop.pricing.quote_price`` lives in ``shop.pricing``."""
    return qualified_name.rpartition(".")[0]
