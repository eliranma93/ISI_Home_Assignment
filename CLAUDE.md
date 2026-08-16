# CLAUDE.md — Satellite Camera Data Manager

## What this is

A home assignment for ISI (Embedded Software). The program simulates one orbit of a small
satellite that takes pictures on a schedule, stores them in limited memory, and downlinks
them during short ground-station windows. Storage and link capacity are **deliberately
oversubscribed** — the subject of the exercise is the keep / discard / send-order decisions.

**The graded deliverable is a live presentation and a design conversation, not the program.**
The code exists to support that conversation. Optimize for something that can be fully
explained and modified live, in front of reviewers.

## Language and toolchain

- **Python 3.11+, standard library only.** No third-party packages, no virtualenv required.
- Modules used: `csv`, `dataclasses`, `enum`, `abc`, `argparse`, `typing`, `unittest`, `fractions`.
- Runs as `python main.py`. Console output only.

## Scope discipline

This is a small program — roughly 500 lines across all modules. Scope creep is the main
failure mode here, so these are hard rules:

- **Build exactly what `docs/PLAN.md` specifies. Nothing else.** If a feature seems useful
  but isn't in the plan, add a line to `docs/NOTES.md` describing it and move on.
- If any single module exceeds ~150 lines, it is doing too much — split it or cut a feature.
- No abstraction that has exactly one use and no second implementation planned. The three
  policy interfaces are the exception, and they are justified because the assignment is
  explicitly about swapping those decisions.
- Prefer a documented limitation over an implementation. A README line saying "quoted CSV
  fields are not supported" is a better answer than 40 lines of quote handling.

## Hard constraints from the brief

- **Deterministic.** Same inputs → byte-identical output, every run. No randomness, no
  time-based values, no iteration over `set` in any path that affects output or ordering.
- Storage capacity is 512 MB and must be trivially changeable (CLI flag plus one constant).
- Reads exactly two CSV files: `pictures.csv`, `passes.csv`.
- Output: a chronological timeline of events, plus a summary (pictures taken / sent /
  discarded, total MB sent, peak storage level).

## Do NOT build

Straight from the brief — treat these as forbidden, not deprioritized:

- No orbital mechanics or physics. The schedule is given.
- No GUI, no networking, no real hardware, no async.
- No persistence between runs, no login, no security.
- No MILP/CP-SAT optimal-benchmark solver. This is presentation material ("what I'd add with
  two more days"), not code.
- No plugin registry, no entry-point discovery, no config-file class loading, no metaclasses.
  Dependency injection here means objects passed as constructor arguments. Nothing more.
- No logging framework, no `logging` module. `print()` with a fixed format string.
- No `pytest`, no `tox`, no coverage tooling. `unittest` from the standard library.

## Architecture

Four layers, three injected interfaces:

```
satsim/
  models.py            Picture, Pass, Importance, Event
  csv_input.py         parsing + validation -> domain objects
  storage.py           Storage: holds pictures, tracks used/peak
  engine.py            Simulator: owns the clock, drives events, records Event objects
  policies/
    value.py           ValueFunction  (ABC)   <- injected into both policies below
    storage_policy.py  StoragePolicy  (ABC)   admit? / evict what?
    downlink_policy.py DownlinkPolicy (ABC)   send what, in what order?
  report.py            timeline + summary formatting
main.py                CLI, constructs policies, injects them
tests/
```

`engine.py` must not contain a single comparison against an importance level, and must not
import any concrete policy class. Every value judgement lives behind an interface. That
separation *is* the thing being demonstrated — if the engine runs without knowing which
policy it holds, the design point is proven.

`ValueFunction` is a shared dependency of both policies. That is intentional: the value model
changes once and affects eviction and transmission consistently, which prevents the classic
bug where the two rank pictures on different scales.

Use `abc.ABC` with `@abstractmethod` for the three interfaces — explicit and readable in a
walkthrough. Type-hint every public function.

## Determinism rules (non-negotiable)

Value density is a ratio, and float ratios are where determinism dies.

- Sizes and link speeds are integers in the CSVs. Keep them `int`. Python integers are exact
  and unbounded, so there is no reason to leave integer arithmetic.
- Represent picture value as a scaled integer (high=100, medium=50, low=20).
- **Never compute `value / size` as a float for comparison.** Compare densities by cross
  multiplication: `a.value * b.size_mb` vs `b.value * a.size_mb`.
- Every sort must use a **total** ordering, with the picture's input row index as the final
  tie-breaker. No two pictures may ever compare equal.
- `sorted()` is stable, which is fine, but do not rely on it — make the key total anyway.

## Window boundary semantics

A pass is **half-open: `[start, end)`**, because capacity is `(end - start) * speed`, which
only holds for a half-open interval. A picture taken at minute `t` is available to send from
minute `t` onward, in the same tick. Both choices must be stated in the README — the input
data has pictures arriving at exactly minutes 25, 30, 70 and 75, so these edges are live, not
hypothetical.

## AI disclosure

The brief requires noting where AI was used and what was changed. Maintain `docs/AI_NOTES.md`
from the first commit — append as you go, do not reconstruct it at the end.

## Definition of done for each phase

The phase's acceptance criteria in `docs/PLAN.md` pass, `docs/NOTES.md` records any limitation
accepted, and there is one commit per phase.
