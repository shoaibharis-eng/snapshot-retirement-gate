"""Read a project's topology from its source, without importing or running it."""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence
from pathlib import Path

from verifier.hashing import digest
from verifier.snapshot.imports import internal_imports
from verifier.snapshot.topology import Symbol, Topology


def extract_topology(root: Path, packages: Sequence[str]) -> Topology:
    """Describe the public symbols and internal imports of ``packages``."""
    symbols: dict[str, Symbol] = {}
    imports: dict[str, tuple[str, ...]] = {}
    for package in packages:
        for path in sorted((root / package).rglob("*.py")):
            module = module_name(root, path)
            tree = _parse(path)
            is_package = path.name == "__init__.py"
            imports[module] = internal_imports(tree, module, is_package, packages)
            for name, symbol in _public_symbols(tree):
                symbols[f"{module}.{name}"] = symbol
    return Topology(symbols, imports)


def module_name(root: Path, path: Path) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _parse(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        # A module that cannot be parsed exposes nothing. Everything it used to
        # export then shows up as removed, which makes the gate hold.
        return ast.Module(body=[], type_ignores=[])


def _public_symbols(tree: ast.Module) -> Iterator[tuple[str, Symbol]]:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public(node.name):
                yield node.name, _function(node)
        elif isinstance(node, ast.ClassDef):
            if _is_public(node.name):
                yield node.name, _class(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and _is_public(target.id):
                    yield target.id, Symbol("constant", "", _fingerprint([node.value]))


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> Symbol:
    return Symbol("function", _signature(node), _fingerprint(node.decorator_list + _body(node)))


def _class(node: ast.ClassDef) -> Symbol:
    methods = [
        member
        for member in node.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (_is_public(member.name) or member.name == "__init__")
    ]
    signature = "; ".join(f"{method.name}{_signature(method)}" for method in methods)
    return Symbol("class", signature, _fingerprint(node.bases + _body(node)))


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    text = f"({ast.unparse(node.args)})"
    if node.returns is not None:
        text += f" -> {ast.unparse(node.returns)}"
    return text


def _body(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[ast.AST]:
    """The statements of a definition, without its docstring."""
    body = list(node.body)
    first = body[0] if body else None
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        body = body[1:]
    return body


def _fingerprint(nodes: Sequence[ast.AST]) -> str:
    """Hash of the syntax tree, so comments and layout do not matter."""
    return digest([_structure(node) for node in nodes])


def _structure(node: object) -> object:
    """A JSON-friendly outline of a syntax tree.

    Positions and empty fields are left out, which keeps the outline the same
    across Python versions that add optional fields to existing nodes.
    """
    if isinstance(node, ast.AST):
        fields = sorted((name, _structure(value)) for name, value in ast.iter_fields(node))
        return [type(node).__name__, [field for field in fields if field[1] not in (None, [])]]
    if isinstance(node, list):
        return [_structure(item) for item in node]
    return None if node is None else repr(node)
