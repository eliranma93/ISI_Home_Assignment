# Work plan — Satellite Camera Data Manager

Read `CLAUDE.md` first. Work one phase at a time, in order. At the end of each phase: stop,
report what was built and any limitation accepted, and wait for review before continuing.

Each phase lists exactly what to build. Anything not listed is out of scope for that phase —
if it seems necessary, say so in the phase report rather than building it.

**If an acceptance criterion contradicts the input data, or contradicts a rule in
`CLAUDE.md`, stop and report the contradiction. Do not silently reconcile it.** These
documents were written by hand and may contain errors; a wrong number in the plan must not
become a wrong constant in the code.

---

## Phase 0 — Skeleton

**Goal:** an empty program that runs end to end, so no later phase is blocked on plumbing.

- Package layout per `CLAUDE.md`, with `__init__.py` files.
- `main.py` parsing CLI args and printing a stub summary:
  ```
  python main.py --pictures pictures.csv --passes passes.csv \
                 --storage-mb 512 \
                 --storage-policy value_density \
                 --downlink-policy density_fractional
  ```
  Defaults: `storage-mb 512`, and the primary policy for each interface.
- Empty `NOTES.md` and `AI_NOTES.md`.

**Acceptance:** `python main.py --help` prints usage and exits 0.
**Commit:** `chore: package skeleton and CLI scaffold`

---

## Phase 1 — Input layer

**Goal:** the two CSVs become validated domain objects, and bad input fails loudly and usefully.

- `models.py` — frozen dataclasses:
  - `Importance(Enum)` with `HIGH`, `MEDIUM`, `LOW`.
  - `Picture(index: int, take_at_min: int, size_mb: int, importance: Importance)`.
  - `Pass(start_min: int, end_min: int, speed_mb_per_min: int)`.
- `csv_input.py` — uses `csv.DictReader`. Header validation, whitespace trimming, integer
  conversion. **Quoted fields and embedded commas are not supported — document this in the
  README instead of handling it.**
- Validation that collects **all** errors before exiting, not just the first. Cover: missing
  or unexpected columns, non-numeric values, size ≤ 0, negative `take_at_min`, unrecognised
  importance string, `end_min <= start_min`, `speed_mb_per_min <= 0`, overlapping passes.
  Report each with its CSV line number, then exit non-zero.
- Sort pictures by `(take_at_min, index)`, passes by `start_min`. `index` is the original row
  number and must survive on every picture — it is the final tie-breaker everywhere.

**Acceptance:** loading the provided files reports `36 pictures, 2 passes`. A crafted bad CSV
prints every offending row with its line number and exits non-zero.
**Commit:** `feat: csv input parsing and validation`

---

## Phase 2 — Engine and clock

**Goal:** a correct simulation driven by placeholder policies. This phase is load-bearing —
do not start Phase 3 until the timeline is right.

- `storage.py` — `Storage` holding pictures by index, tracking `used_mb`, `capacity_mb` and
  `peak_used_mb`.
- `engine.py` — `Simulator` advancing minute by minute from 0 through the last relevant
  minute. Within each minute, in this fixed order:
  1. **Arrivals** — every picture with `take_at_min == now`, in row order.
  2. **Transmission** — if `now` falls inside a pass (half-open `[start, end)`), that minute's
     budget is `speed_mb_per_min`; ask the `DownlinkPolicy` what to send, then consume budget.
- Arrivals precede transmission within a minute, so a picture taken at minute 25 is sendable
  at minute 25. **State this in the README — it is a real design choice, and the data
  exercises it six times.**
- Transmission supports **chunking with resume**: a picture tracks `sent_mb`, and leaves
  storage only when `sent_mb == size_mb`. A partially sent picture survives to the next
  window and continues from its offset.
- Every state change appends an `Event` record `(minute, kind, picture_index, detail)`. Kinds:
  `TAKEN`, `STORED`, `SKIPPED`, `EVICTED`, `SEND_START`, `SEND_PROGRESS`, `SEND_COMPLETE`.
  **The engine records; it never prints.** Reporting is Phase 4.
- **Define the three abstract base classes in this phase, not Phase 3** — `ValueFunction`,
  `StoragePolicy`, `DownlinkPolicy`, with the signatures given in Phase 3. The engine is
  written against the interfaces from its first line, so Phase 3 only adds implementations.
- Placeholder implementations for this phase only: `FitsOrSkipStorage` (store if it fits,
  otherwise skip) and `ArrivalOrderDownlink`. Both are deleted in Phase 3.

**Acceptance:** runs over the real data without error; peak storage never exceeds 512 MB;
total MB sent never exceeds 1350; two consecutive runs produce identical event lists.
**Commit:** `feat: simulation engine with minute clock and chunked transmission`

---

## Phase 3 — Policies behind interfaces

**Goal:** the actual subject of the assignment. Two implementations per interface, so the
seam is demonstrated rather than asserted.

### `policies/value.py`
```python
class ValueFunction(ABC):
    @abstractmethod
    def value_of(self, picture: Picture, now_min: int) -> int: ...
```
- `ImportanceValue` — `HIGH=100`, `MEDIUM=50`, `LOW=20`. That is the whole class.

### `policies/storage_policy.py`
```python
class StoragePolicy(ABC):
    @abstractmethod
    def on_arrival(self, incoming: Picture, storage: Storage, now_min: int) -> Decision: ...
    # Decision: Store() | Skip(reason) | EvictThenStore(indices)
```
- **`ImportanceThenAgeStorage`** (baseline) — evict lowest importance first, oldest first
  within a level. This is where most candidates stop, which makes it the right thing to beat.
- **`ValueDensityStorage`** (primary) — the GDS-derived policy. Rank stored pictures by value
  density ascending and accumulate eviction candidates until the incoming picture fits.
  **Admit only if `value(incoming) > sum of values of the eviction set`** — absolute value,
  not density, because both sides occupy the same bytes. Otherwise `Skip`.
  - Do **not** implement the GDS `L` inflation term. Write a class docstring stating that
    GDS's aging term exists to handle repeated access, that pictures here are written once and
    read once, and that carrying `L` would eventually let a stale medium evict a high. This
    docstring is a presentation talking point — it shows the algorithm was understood rather
    than copied.
  - A picture with `sent_mb > 0` is only evicted if it is the only candidate; record this
    choice in `NOTES.md`.

### `policies/downlink_policy.py`
```python
class DownlinkPolicy(ABC):
    @abstractmethod
    def select(self, storage: Storage, budget_mb: int, now_min: int) -> list[SendOrder]: ...
```
- **`ImportanceFirstAtomic`** (baseline) — highest importance first, skipping any picture
  that does not fit whole in the remaining budget.
- **`DensityFractionalDownlink`** (primary) — fractional knapsack: sort by value density
  descending, fill the budget, split the boundary picture and let it resume next window.
  Docstring must state: this is **provably optimal for delivered value-MB, and optimal for
  delivered value only because chunking with resume exists** — without resume, the greedy
  would be counting value that never reaches the ground.

Policies are selected by CLI flag, constructed in `main.py`, and passed into `Simulator` as
constructor arguments. **`engine.py` must not import any concrete policy class.**

**Acceptance:** all four policy combinations run and produce different, defensible summaries;
`engine.py` contains no reference to `Importance`; and — the criterion that actually proves
the design — **`git diff` shows `engine.py` and `storage.py` were not modified at all in this
phase.** If either had to change, the interfaces from Phase 2 were wrong; say so in the phase
report rather than patching around it.
**Commit:** `feat: swappable storage and downlink policies via injection`

---

## Phase 4 — Reporting

**Goal:** output a reviewer can follow on a shared screen during a live demo.

- Timeline, one line per event, fixed-width columns, chronological:
  ```
  [min 025] SENT      #12   43MB  high     storage 468/512
  [min 021] EVICTED   #03   64MB  low      storage 448/512   for #09
  ```
- Summary block: pictures taken / stored / skipped / evicted / fully sent / partially sent,
  total MB sent, peak storage MB, and **total value delivered** — name that metric explicitly,
  since it is what the policies actually optimize and it makes the comparison honest.
- **An "unreachable" section**: pictures still in storage at end of run, and separately those
  taken too late to be sendable at all. Under the half-open convention the last pass is
  `[70, 75)`, so the final transmitting minute is 74 and a picture taken at minute 75 is
  already unreachable. The provided data therefore contains **8 such pictures totalling
  636 MB**, including a 107 MB `high` taken at exactly minute 75.
  - Note the trap: taking the naive cut `take_at_min > 75` gives 7 pictures / 529 MB and
    silently contradicts the capacity formula. The boundary picture is the whole point —
    report the number the code actually derives from the pass list, never a hardcoded
    constant, and assert the derived value equals 8 / 636 MB for the provided data.
  - Surfacing this section is the cheapest possible way to show the data was read and not
    merely processed.
- `--quiet` flag printing only the summary, for building the comparison table.

**Acceptance:** a shell loop runs all four policy combinations with `--quiet` and yields a
four-row comparison suitable for pasting into the presentation.
**Commit:** `feat: timeline and summary reporting`

---

## Phase 5 — Tests

**Goal:** show the edge cases were considered. Use `unittest` from the standard library, with
small synthetic CSV fixtures written to a temp directory.

1. Picture larger than total storage capacity → skipped, never stored, logged once.
2. Picture larger than free space, higher value than the eviction set → evicts and stores.
3. Same, but lower value than the eviction set → skipped, incumbents survive.
4. Window ends mid-picture → partial send recorded, remainder resumes in the next window.
5. Picture taken at exactly `window_start` → sendable in that same minute.
6. Picture taken at exactly `window_end` → **not** sendable (half-open interval).
7. Picture taken after the last window closes → stored, reported as unreachable.
8. Empty `pictures.csv` → clean run, zeroed summary, exit 0.
9. Malformed row → every error reported, exit non-zero.
10. Determinism → run the real dataset twice, assert identical output strings.

**Acceptance:** `python -m unittest discover tests` reports 10 passing tests.
**Commit:** `test: edge cases and determinism`

---

## Phase 6 — Documentation

- `README.md` — how to run, the CLI flags, the four policy combinations, and a
  **"Decisions and tradeoffs"** section covering: half-open windows, arrivals-before-transmission
  ordering, integer cross-multiplication for density comparison, no quoted-CSV support, the
  omitted `L` term in the GDS-derived policy, and chunking with resume.
- `NOTES.md` — everything simplified or left out, with what would replace it.
- `AI_NOTES.md` — final pass over where AI was used and what was changed.
- `PRESENTATION.md` — bullets answering the four questions below.

**Commit:** `docs: readme, tradeoffs and presentation notes`

---

## If scope must be reduced

Drop in this order, and record each as a deliberate tradeoff in `NOTES.md`:

1. `--quiet` flag → run the four combinations manually.
2. Tests 8–10 → keep 1–7, which are the ones tied to the real data.
3. `ImportanceThenAgeStorage` baseline → keep only the primary policy and describe the
   baseline verbally. **Cut this before cutting the interface** — the seam is the point, and
   an interface with a single implementation still demonstrates it.

**Never cut:** determinism, the interface boundaries, or the README tradeoffs section.

---

## The presentation must answer these four

1. **Design and why** — especially discard and send-order → the two policy docstrings plus
   the four-row comparison table.
2. **Run it live, showing storage filling and a window running out of time** → the real data
   does both unprompted: storage first overflows around minute 21, before the first window
   even opens, and both windows exhaust their budget mid-picture.
3. **The trickiest part** → candidate answer: making density comparison deterministic without
   floats, and deciding whether a partially transmitted picture may be evicted.
4. **What I'd add with two more days, and what I deliberately left out** → an offline
   MILP/CP-SAT solver to measure how close the online policy gets to a clairvoyant optimum;
   progressive image quality layers so downlink stops being all-or-nothing; multi-window
   lookahead that reserves budget in the first window for high-value arrivals expected before
   the second.
