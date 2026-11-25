# Where it breaks

Known limitations and failure cases, most important first.

## 1. The honest repair nobody logged

The gate cannot tell an honest unlogged repair from a loop chasing green. Both
are an interface change that no scope covers. In scenario 3 the repair is
correct, the failures are confined to the moved function, and the gate still
holds.

- **Every honest unlogged repair stalls the loop** until a human answers. If
  such repairs are common, the gate becomes a queue.
- **The question it asks is drafted from the implementation.** The suggested
  scope is inferred from the diff, which the agent wrote. A reviewer who
  approves drafts without reading them has moved the authorisation back to the
  agent. The trace labels the draft as a question for this reason.
- **Ratifying after the fact is allowed.** Scenario 6 shows a human appending
  the scope after the repair. The gate cannot tell an instruction that came
  before a repair from one written afterwards to justify it. It relies on the
  agent being unable to write to the log.
- **Legitimacy is not checked.** The gate never asks whether the boundary
  change was actually needed to fix the import. It only reports that it
  happened and was not covered.

## 2. The behavioural evidence is only as good as the frozen suite

`preserved` replays the frozen tests against the successor. It proves that the
behaviour the suite *asserts* survived the rename, and nothing more.

- A behaviour change that no frozen test observes is retired cleanly.
- Code that no frozen test runs is not exercised at all. A leftover
  `from module import old_name` is still caught, because the gate sees the
  import in the topology. A leftover use through the module, such as
  `module.old_name(...)`, in code no test runs is not caught.
- The body comparison narrows this, but only for the renamed symbol's own body.
  A change inside a helper it calls is invisible to the comparison. A changed
  body with a passing replay produces a caveat, not a hold.
- A flaky test counts as a failure. The gate does not retry.

## 3. Only renames can be authorised

The scope vocabulary has one operation. Everything else holds for a human:

- signature changes, even backwards-compatible ones (scenario 4);
- one interface split into two, or two merged into one;
- removing an interface with no successor.

Re-binding needs a one-to-one mapping with an unchanged signature. A signature
change would need an adapter, and an adapter is new test-side code, which is
too close to regenerating tests. A whole-module move works but has to be
authorised symbol by symbol.

## 4. Re-binding has blind spots

- A retired name is answered only for code running in a frozen suite module,
  so that a caller the repair forgot is not hidden. This is decided by looking
  at which module is asking, using `sys._getframe`, which is specific to
  CPython.
- A test that reaches the old name indirectly is therefore not served: a
  string patch such as `mock.patch("a.b.old")`, or a helper that lives outside
  the tests directory. That test fails under replay, and the gate reports a
  violated obligation that is really a limit of the harness. It errs toward
  not retiring cleanly.
- When the old module is gone entirely, an empty stand-in module takes its
  place during the replay. The stand-in exists for everyone, so a leftover
  bare `import old_module` in the implementation is not caught by the replay.
- Code under test can detect that it is being replayed and behave differently.
- The child interpreter is not a sandbox. Running the suite runs repaired code.

## 5. Pins and failures are attributed statically

- Pins come from the import statements of each test file. A test that reaches
  an interface another way (an import inside a helper, `getattr`, a fixture)
  is not pinned to it.
- Pins are per file. A module-level import failure takes down every test in
  the file, so that is the granularity failures have anyway.
- Tests are listed statically too: methods named `test...` that are defined
  directly in a class of the file. A test inherited from a base class, or
  generated at run time, is not counted.
- A failure counts as "on the boundary" only if the file could not be imported
  and the file is pinned to a changed boundary. A test that looks the name up
  at call time fails with `AttributeError` inside the test, counts as a
  behavioural failure, and makes the gate hold. This errs toward holding.

## 6. The topology is static and Python-only

- Public means "top-level name without a leading underscore". `__all__` is
  ignored.
- Re-exports are not symbols. If a repair moves a function and leaves
  `from new import name` behind, the snapshot says the symbol is gone while
  the old tests still pass. Unauthorised, that holds even though the suite is
  green. Authorised, it still holds if any module keeps importing through the
  old path.
- A compatibility alias (`old = new`) makes the old name a constant. The
  rename then counts as not carried out and the gate holds.
- Decorators that change a signature, dynamic attributes and conditional
  definitions are not understood.
- A module with a syntax error is treated as exporting nothing. The gate holds,
  but the trace reports removed symbols and not the syntax error.

## 7. The trust boundaries are conventions here

In this prototype everything runs as one user in one process. The separation
the design depends on is not enforced.

- The hash chain detects edits, removals and reorders. It does not detect
  removing the **newest** entries, because nothing outside the log knows how
  long it should be. That removes authority, so it fails toward holding.
- `issued_by` is an unauthenticated string. Nothing stops an agent writing
  `human:reviewer` if it can write to the log at all.
- The snapshot's id detects corruption of the file. A consistent rewrite of the
  snapshot and its id is not detected unless the id is kept somewhere the
  agent cannot reach.
- The suite is hashed and then run from the working copy, not from a sealed
  copy. Only `.py` files under the tests directory are hashed, so a data
  fixture could change unnoticed.

A real deployment needs the log and the snapshot in a store the repair agent
has no write access to, and signed entries.

## 8. Scope breaches are all or nothing

One out-of-scope change holds everything, including a clean authorised rename
made in the same repair. That is deliberate: a repair that did more than it was
asked is not trusted in part. It also means one stray edit blocks unrelated,
legitimate retirements.

The import rule is also loose on one side. Any import change inside the two
modules a rename touches is accepted as part of the rename, so a new dependency
added there rides along.

## 9. Obligations accumulate

Nothing is ever re-frozen. Carried tests stay bound through the log forever,
and each evaluation recomputes from the original snapshot and the whole log.
There is no path for retiring a behavioural obligation on purpose, for example
when a requirement really changes. That would need a second kind of scope and
its own evidence, and it is the point where "never regenerate tests" stops
being a sufficient rule.

## 10. Smaller gaps

- When several renames are replayed together, a failure is not attributed to
  one of them. All of them get `RETIRE_INTERFACE_ONLY`.
- If the child interpreter crashes, or the suite runs for more than two
  minutes, the gate raises an error instead of returning `HOLD`. Nothing is
  retired, but no trace is written either.
- Appends to the log are not safe against concurrent writers.
- Fingerprints are compared structurally. Two bodies that behave the same but
  are written differently count as changed.
