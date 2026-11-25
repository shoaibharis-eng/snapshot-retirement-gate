"""Topology snapshot: the project's shape and the suite's bytes at freeze time."""

from verifier.snapshot.extract import extract_topology
from verifier.snapshot.snapshot import Layout, Snapshot, SnapshotIntegrityError, freeze
from verifier.snapshot.suite import FrozenFile, describe_suite, suite_drift
from verifier.snapshot.topology import Symbol, Topology, module_of

__all__ = [
    "FrozenFile",
    "Layout",
    "Snapshot",
    "SnapshotIntegrityError",
    "Symbol",
    "Topology",
    "describe_suite",
    "extract_topology",
    "freeze",
    "module_of",
    "suite_drift",
]
