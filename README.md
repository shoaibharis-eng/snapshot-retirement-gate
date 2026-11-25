# Snapshot Retirement Gate

A repair loop reruns a **frozen** test suite until it passes. When a repair
renames or moves an interface, the suite starts failing, and something has to
decide which side is wrong: **is the suite stale, or is the implementation
broken?**

This is a small verifier that makes that call from evidence. It never creates
or rewrites a test.

## Quick start

Python 3.9 or newer. Standard library only, nothing to install.

```
python3 -m reproduction      # replay every scenario, regenerate traces/
python3 -m unittest          # run the tests
```

The first command prints one verdict per scenario:

```
#  scenario                  verdict                as expected
1  clean-rename              RETIRE                 yes
2  rename-changes-behaviour  RETIRE_INTERFACE_ONLY  yes
3  unlogged-repair           HOLD                   yes
4  scope-overreach           HOLD                   yes
5  collateral-failure        HOLD                   yes
6  human-ratifies            HOLD then RETIRE       yes
7  suite-edited              HOLD                   yes
```

`python3 -m reproduction 2` prints the full decision trace of one scenario.

## The idea

**The gate retires a name, never a behaviour.**

An authorised rename proves that the old *name* is obsolete. It proves nothing
about what the code behind the name should do. So the gate never drops the old
tests after a rename. It runs them again, byte for byte unchanged, with the old
name pointed at the new one.

- If they pass, the old interface is retired cleanly.
- If they fail, the name is retired but the tests still bind, and it is the
  implementation that is wrong.

The repair loop is then neither pulled back toward the old interface nor
released from what the old tests demanded.

## How the gate decides

The gate relies on three things: an append-only **instruction log** in which
every entry states what it may change, a **topology snapshot** taken when the
suite was frozen, and **what it observes** when it runs the frozen suite. It
never reads the agent's own account of a repair.

| # | Condition | Question | If the answer is no |
|---|---|---|---|
| 0 | `integrity` | Are the frozen suite and the log untouched? | `HOLD` |
| 1 | `authorised` | Does a logged scope cover every boundary change? | `HOLD`, and the gate names the scope it needs from a human |
| 2 | `contained` | Does the whole interface delta stay inside that scope? | `HOLD` |
| 3 | `confined` | Does the frozen suite fail only on the changed boundary? | `HOLD` |
| 4 | `preserved` | Re-bound through the log, do the old tests still pass? | `RETIRE_INTERFACE_ONLY` |

Five times yes is `RETIRE`. If nothing changed at all, there is nothing to
retire and the gate holds.

Conditions 1 to 3 are the agreed minimum. Condition 4 is the further evidence
that scenario 2 needs, and condition 0 guards the records themselves.

## What separates scenario 2 from scenario 1

In both, the same log entry authorises the same rename, and all five pricing
tests fail at import. Conditions 0 to 3 pass in both.

| Evidence | 1. Clean rename | 2. Rename that changes behaviour |
|---|---|---|
| Interface delta | 4 changes, all authorised | Identical |
| Frozen suite, exactly as frozen | 5 cannot load, 4 pass | Identical |
| The agent's own account | "Renamed quote_price to price_for..." | Word for word the same |
| **Old tests re-bound to the new name** | **9 of 9 pass** | **8 of 9 pass** |
| Body of the renamed function | Unchanged since the freeze | Changed |
| Verdict | `RETIRE` | `RETIRE_INTERFACE_ONLY` |

In scenario 2 the repair also moved the bulk discount from ten units to eleven.
`test_bulk_discount_starts_at_ten_units` catches it under the new name. The
gate reports the implementation as wrong and tells the loop to fix the
behaviour, not to restore the old name.

The body comparison is supporting evidence only. If the old tests pass but the
body changed, the gate still retires and adds a caveat: behaviour that no
frozen test asserts is unverified.

## Scenarios

Each link is the decision trace for that scenario: what the gate saw, which
conditions passed or failed, and the verdict.

| # | Scenario | Verdict | What it shows |
|---|---|---|---|
| 1 | [Clean rename](traces/1-clean-rename.md) | `RETIRE` | The reference case |
| 2 | [Rename that also changes behaviour](traces/2-rename-changes-behaviour.md) | `RETIRE_INTERFACE_ONLY` | Authorisation alone is not enough |
| 3 | [Honest repair nobody logged](traces/3-unlogged-repair.md) | `HOLD` | The gate names the scope decision it needs |
| 4 | [The repair exceeds its scope](traces/4-scope-overreach.md) | `HOLD` | `contained` fails: an extra change that no test notices |
| 5 | [Failures outside the boundary](traces/5-collateral-failure.md) | `HOLD` | `confined` fails: the repair also broke something unrelated |
| 6 | [A human answers the question](traces/6-human-ratifies.md) | `HOLD` then `RETIRE` | Only a log entry turns a hold into a retirement |
| 7 | [The repair edits the suite](traces/7-suite-edited.md) | `HOLD` | `integrity` fails: a modified suite is not evidence |

Scenarios 1 to 3 are the required ones. The rest are controls: 4, 5 and 7 each
fail exactly one of conditions 0 to 3, and 6 continues scenario 3.

The traces are generated by the tool. A test fails if a committed trace is out
of date.

## Where everything is

| Piece | Where |
|---|---|
| **Reproduction project that drifts** | [`reproduction/`](reproduction): the toy shop in `project/`, scripted repairs in `drift.py`, scenarios in `scenarios/` |
| **Append-only instruction log** | [`verifier/log/`](verifier/log) |
| **Topology snapshot** | [`verifier/snapshot/`](verifier/snapshot) |
| **Retirement gate** | [`verifier/gate/`](verifier/gate): start with `gate.py` and `checks.py` |
| Suite runner and re-binding | [`verifier/suite/`](verifier/suite) |
| Trace rendering | [`verifier/trace/`](verifier/trace) |
| Tests | [`tests/`](tests) |
| Generated decision traces | [`traces/`](traces) |

## Design notes

<details>
<summary>Six short points on how the pieces work. Click to expand.</summary>

- **Scope vocabulary.** One operation: `rename a.b.old to a.b.new`, which also
  covers moving a symbol to another module. An empty scope means
  "implementation only". Renames compose across entries, and for the same name
  a later entry wins.
- **What a rename covers.** Removing the old name, adding the new one with the
  same signature, importers switching over, and import changes inside the two
  modules involved. Anything else is outside the scope. A module that still
  imports the old name means the rename was not carried through.
- **Tamper evidence.** Log entries are chained by hash, so an edit, a removal
  or a reorder is detected. The snapshot stores the hash of every suite file
  and where the log stood at the freeze, so only later entries can retire
  anything.
- **Re-binding is for the tests only.** The old name is answered only when a
  frozen test file asks for it. Implementation code that still uses the old
  name fails, as it would for real.
- **No stored state.** Every verdict is recomputed from the snapshot, the log
  and the project as it is. "Retired" is a derived fact, not a flag that
  someone could flip.
- **Failing safe.** Whenever the gate cannot tell, it holds.

</details>

## Where it breaks

[LIMITATIONS.md](LIMITATIONS.md) is the full list, starting with the honest
repair nobody logged. The three that matter most:

- An honest unlogged repair looks the same as a loop chasing green, so it
  always stalls until a human answers.
- The behaviour check is only as strong as the frozen tests. A change that no
  frozen test observes is retired cleanly.
- Only renames and moves can be authorised. Signature changes, splits and
  removals always hold.

## Development

`make check` runs the tests and replays every scenario. `make lint` runs
[ruff](https://docs.astral.sh/ruff/), the only tool here that is not in the
standard library; nothing needs it to run. CI is set up to run both on every
push.
