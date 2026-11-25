"""Command line: replay scenarios and write their decision traces.

python3 -m reproduction            replay everything, refresh traces/
python3 -m reproduction 2          print the full trace of one scenario
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from reproduction.replay import replay_in_scratch
from reproduction.report import summary_table, trace_document, trace_filename
from reproduction.scenarios import SCENARIOS, find

TRACES = Path(__file__).resolve().parent.parent / "traces"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m reproduction",
        description="Replay drift scenarios through the retirement gate.",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        help="number or name of one scenario; omit to replay all of them",
    )
    parser.add_argument(
        "--traces",
        type=Path,
        default=TRACES,
        help="directory the decision traces are written to (default: traces/)",
    )
    args = parser.parse_args(argv)

    if args.scenario is not None:
        try:
            scenario = find(args.scenario)
        except KeyError:
            names = ", ".join(f"{s.number} ({s.slug})" for s in SCENARIOS)
            parser.error(f"unknown scenario {args.scenario!r}; choose from {names}")
        run = replay_in_scratch(scenario)
        print(trace_document(run), end="")
        return 0 if run.as_expected() else 1

    runs = [replay_in_scratch(scenario) for scenario in SCENARIOS]
    args.traces.mkdir(parents=True, exist_ok=True)
    for run in runs:
        (args.traces / trace_filename(run)).write_text(trace_document(run), encoding="utf-8")
    print(summary_table(runs))
    print(f"\nDecision traces written to {args.traces}")
    return 0 if all(run.as_expected() for run in runs) else 1
