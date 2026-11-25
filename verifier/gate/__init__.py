"""The retirement gate: evidence in, verdict out."""

from verifier.gate.decision import (
    Decision,
    Finding,
    RetiredBoundary,
    ScopeRequest,
    Status,
    Verdict,
)
from verifier.gate.delta import Change, ChangeKind, interface_delta
from verifier.gate.evidence import Evidence, collect
from verifier.gate.gate import evaluate, judge
from verifier.gate.provenance import AuthorisedRename, Provenance, net_renames, trace_provenance

__all__ = [
    "AuthorisedRename",
    "Change",
    "ChangeKind",
    "Decision",
    "Evidence",
    "Finding",
    "Provenance",
    "RetiredBoundary",
    "ScopeRequest",
    "Status",
    "Verdict",
    "collect",
    "evaluate",
    "interface_delta",
    "judge",
    "net_renames",
    "trace_provenance",
]
