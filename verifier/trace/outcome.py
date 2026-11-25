"""The judgement part of a trace: conditions, consequences, open questions."""

from __future__ import annotations

from verifier.gate import Decision, Verdict
from verifier.trace.markdown import code_list, table


def conditions(decision: Decision) -> str:
    rows = [(f.check, f.question, f"**{f.status.value}**", f.summary) for f in decision.findings]
    lines = [table(("Condition", "Question", "Result", "Finding"), rows)]
    details = [f"- {f.check}: {detail}" for f in decision.findings for detail in f.details]
    return "\n".join(lines + ([""] + details if details else []))


def consequences(decision: Decision) -> str:
    lines = []
    for boundary in decision.retired:
        lines.append(
            f"- Retired: `{boundary.old}`. Successor: `{boundary.successor}`, "
            f"authorised by entry #{boundary.entry_seq}."
        )
    if decision.carried:
        lines.append(
            f"- Carried forward: {len(decision.carried)} frozen tests stay binding, "
            "now against the successor. None is rewritten."
        )
    lines += [f"- Violated obligation: `{o.id}` ({o.reason})" for o in decision.violated]
    if decision.violated:
        lines.append(
            "- Next repair: fix the behaviour under the new name. Do not restore the old name."
        )
    lines += [f"- Caveat: {caveat}" for caveat in decision.caveats]
    if decision.verdict is Verdict.HOLD:
        lines.append("- Nothing is retired. Every frozen test stays binding against the snapshot.")
    return "\n".join(lines)


def scope_request(decision: Decision) -> str:
    request = decision.scope_request
    if request is None:
        return ""
    lines = ["**Scope decision needed from a human**", ""]
    if request.boundaries:
        names = code_list(request.boundaries)
        lines += [f"The frozen suite depends on {names}, and no log entry allows changing it.", ""]
    if request.suggested:
        lines.append(
            "If the change is intended, append an entry with this scope to the instruction "
            "log. The draft is inferred from the diff, so it is a question, not evidence:"
        )
        lines += [f"- {rename.describe()}" for rename in request.suggested]
    else:
        lines.append(
            "The scope vocabulary cannot express what is listed under `contained`, "
            "so it needs a manual review."
        )
    lines += [
        "",
        "If the change is not intended, revert the repair. "
        "Until one of the two happens, the snapshot holds.",
    ]
    return "\n".join(lines)
