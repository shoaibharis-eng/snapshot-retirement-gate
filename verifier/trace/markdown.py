"""The little Markdown the traces need."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(_cell(text) for text in row) + " |" for row in rows]
    return "\n".join(lines)


def _cell(text: str) -> str:
    """A signature such as ``(x: int | None)`` must not end the table cell."""
    return text.replace("|", "\\|")


def code_list(names: Iterable[str]) -> str:
    """``a``, ``b`` and so on, each formatted as code."""
    return ", ".join(f"`{name}`" for name in names)
