"""Resolve the project-internal names a Python file imports."""

from __future__ import annotations

import ast
from collections.abc import Sequence


def internal_imports(
    tree: ast.AST, module: str, is_package: bool, packages: Sequence[str]
) -> tuple[str, ...]:
    """Qualified names imported from ``packages``, anywhere in the file.

    ``from shop.pricing import quote_price`` yields ``shop.pricing.quote_price``
    and ``import shop.pricing`` yields ``shop.pricing``. Imports inside
    functions count too, because they are still dependencies.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _absolute_base(node, module, is_package)
            names.update(
                base if alias.name == "*" else f"{base}.{alias.name}" for alias in node.names
            )
    return tuple(sorted(name for name in names if name.split(".")[0] in packages))


def _absolute_base(node: ast.ImportFrom, module: str, is_package: bool) -> str:
    """The module a ``from ... import`` reads from, with relative dots resolved."""
    if node.level == 0:
        return node.module or ""
    package = module.split(".") if is_package else module.split(".")[:-1]
    anchor = package[: len(package) - (node.level - 1)]
    return ".".join(anchor + ([node.module] if node.module else []))
