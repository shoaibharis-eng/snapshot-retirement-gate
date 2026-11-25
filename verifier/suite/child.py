"""Run frozen test files inside a child interpreter and report as JSON.

This file is executed as a script by ``verifier.suite.runner``. It must stay
standard-library only and must not import the verifier, because the only
project on its path is the one under test.

Re-binding is what lets a frozen test reach a renamed interface. Before the
tests are imported, each retired name is made to resolve to its successor.
The test files are never touched; only name resolution is redirected, only
along the renames the caller passes in, and only for the frozen suite itself.
"""

import contextlib
import importlib
import json
import sys
import types
import unittest


def main() -> None:
    project = sys.argv[1]
    request = json.load(sys.stdin)
    sys.path.insert(0, project)
    suite_modules = {_module_name(path) for path in request["suite"]}
    with contextlib.redirect_stdout(sys.stderr):
        report = {
            "binding_errors": install_bindings(request["bindings"], suite_modules),
            "files": {path: run_file(path) for path in request["files"]},
        }
    json.dump(report, sys.stdout)


def install_bindings(bindings, suite_modules):
    """Make every old name resolve to its successor. Returns what went wrong."""
    errors = []
    served = {}
    for old, new in sorted(bindings.items()):
        try:
            old_module, _, old_name = old.rpartition(".")
            new_module, _, new_name = new.rpartition(".")
            successor = getattr(importlib.import_module(new_module), new_name)
            served.setdefault(_module_or_stand_in(old_module), {})[old_name] = successor
        except Exception as error:
            errors.append(f"{old} -> {new}: {type(error).__name__}")
    for owner, names in served.items():
        _serve_to_suite(owner, names, suite_modules)
    return errors


def _serve_to_suite(owner, names, suite_modules):
    """Answer the retired ``names`` of ``owner``, but only for the frozen suite.

    A plain alias would bring a retired name back for the implementation too.
    A caller the repair forgot to update would then pass under replay while
    being broken for real. So the names are answered by a module-level
    ``__getattr__`` that checks which module is asking.
    """
    fallback = owner.__dict__.get("__getattr__")

    def module_getattr(requested):
        asking_module = sys._getframe(1).f_globals.get("__name__")
        if requested in names and asking_module in suite_modules:
            return names[requested]
        if fallback is not None:
            return fallback(requested)
        raise AttributeError(f"module {owner.__name__!r} has no attribute {requested!r}")

    owner.__getattr__ = module_getattr


def _module_or_stand_in(name):
    """Import ``name``, or stand in an empty module if it no longer exists."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name is None or not f"{name}.".startswith(f"{error.name}."):
            raise
    stand_in = types.ModuleType(name)
    sys.modules[name] = stand_in
    parent, _, leaf = name.rpartition(".")
    if parent:
        setattr(_module_or_stand_in(parent), leaf, stand_in)
    return stand_in


def _module_name(path):
    name = path[: -len(".py")].replace("/", ".")
    return name[: -len(".__init__")] if name.endswith(".__init__") else name


def run_file(path):
    try:
        module = importlib.import_module(_module_name(path))
    except Exception as error:
        return {"load_error": type(error).__name__, "tests": {}}
    results = {}
    for test in _flatten(unittest.defaultTestLoader.loadTestsFromModule(module)):
        recorder = _Recorder()
        # Run through a suite of one, so class and module fixtures still run.
        unittest.TestSuite([test]).run(recorder)
        name = f"{type(test).__name__}.{test._testMethodName}"
        results[name] = {
            "status": "fail" if recorder.problem else "pass",
            "reason": recorder.problem,
        }
    return {"load_error": None, "tests": results}


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


class _Recorder(unittest.TestResult):
    """Remembers why a single test did not pass cleanly."""

    def __init__(self):
        super().__init__()
        self.problem = ""

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.problem = _describe(err)

    def addError(self, test, err):
        super().addError(test, err)
        self.problem = _describe(err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.problem = _describe(err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.problem = "skipped"

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.problem = "unexpected success"


def _describe(err):
    exception_type, exception, _ = err
    message = str(exception).strip().splitlines()
    summary = f"{exception_type.__name__}: {message[0]}" if message else exception_type.__name__
    return summary[:200]


if __name__ == "__main__":
    main()
