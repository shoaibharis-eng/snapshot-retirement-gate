"""Scope: the interface changes a repair instruction is allowed to make.

The vocabulary is deliberately small. A scope lists renames of public symbols,
each from one qualified name to another, which also covers moving a symbol to
a different module. An empty scope means "implementation only": the
instruction may not change any interface at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_QUALIFIED_NAME = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)+$")


class ScopeError(ValueError):
    """Raised when a scope cannot be expressed in the vocabulary."""


@dataclass(frozen=True)
class Rename:
    """Permission to move one public symbol from ``old`` to ``new``."""

    old: str
    new: str

    def __post_init__(self) -> None:
        for name in (self.old, self.new):
            if not _QUALIFIED_NAME.match(name):
                raise ScopeError(f"not a qualified symbol name: {name!r}")
        if self.old == self.new:
            raise ScopeError(f"a rename must change the name: {self.old!r}")

    def describe(self) -> str:
        return f"rename {self.old} to {self.new}"

    def to_json(self) -> dict[str, str]:
        return {"op": "rename", "from": self.old, "to": self.new}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Rename:
        if data.get("op") != "rename":
            raise ScopeError(f"unsupported boundary change: {data.get('op')!r}")
        return cls(old=data["from"], new=data["to"])


@dataclass(frozen=True)
class Scope:
    """Everything one instruction may change at the interface level."""

    renames: tuple[Rename, ...] = ()

    def describe(self) -> str:
        if not self.renames:
            return "implementation only, no boundary change allowed"
        return "; ".join(rename.describe() for rename in self.renames)

    def to_json(self) -> dict[str, Any]:
        return {"boundary_changes": [rename.to_json() for rename in self.renames]}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Scope:
        return cls(tuple(Rename.from_json(item) for item in data["boundary_changes"]))
