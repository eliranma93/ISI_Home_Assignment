# Satellite Camera Data Manager

A small satellite takes pictures, tries to stash them in memory that's too small for
all of them, and downlinks what it can during two short ground-station passes with a
slow link. Storage and bandwidth are **deliberately oversubscribed** - the interesting part is
the keep / discard / send-order decisions, not the code that runs it.

Python 3.11+, standard library only. No installation step.

## Running it

```
python main.py --pictures pictures.csv --passes passes.csv
```

That uses the defaults (512 MB storage, the primary policy for each interface). A
fully-specified invocation looks like:

```
python main.py --pictures pictures.csv --passes passes.csv \
               --storage-mb 512 \
               --storage-policy value_density \
               --downlink-policy density_fractional
```

Run the test suite with:

```
python -m unittest discover tests
```

13 tests. The first 10 (`docs/PLAN.md` Phase 5) run against synthetic CSV fixtures
except the last:

| # | Covers |
|---|---|
| 1 | Picture larger than total storage capacity - skipped, never stored |
| 2 | Picture larger than free space, higher value than the eviction set - evicts and stores |
| 3 | Same, but lower value than the eviction set - skipped, incumbents survive |
| 4 | Window ends mid-picture - partial send recorded, remainder resumes next window |
| 5 | Picture taken at exactly `window_start` - sendable that same minute |
| 6 | Picture taken at exactly `window_end` - **not** sendable (half-open interval) |
| 7 | Picture taken after the last window closes - stored, reported unreachable |
| 8 | Empty `pictures.csv` - clean run, zeroed summary, exit 0 |
| 9 | Malformed row - every error reported, exit non-zero |
| 10 | Determinism - the real dataset run twice, identical output strings |

Tests 1-7 exercise the engine/storage/policies directly via a shared `tests/helpers.py`;
8-10 go through `main.main()` with stdout/stderr captured, since "exits non-zero" and "a
clean run" are CLI-level contracts.

Three more, added later in `tests/test_density_sort.py`, unit-test
`sorted_ascending_by_density` directly: ascending order across three distinct densities,
tie-breaking by row index when two pictures have exactly equal density, and that the
function returns a new list rather than mutating its input. Not covered anywhere: eviction
of an already-partially-sent picture specifically (see "Evicting a partially-sent picture"
below) - that path is exercised by construction and the policy's docstring, not by an
automated test.

**In VS Code:** `.vscode/launch.json` ships with four ready-to-go debug configurations -
the real data with the default policies, the real data with both baselines, the real
data with `--dump-events`, and `unittest discover` - so you can set a breakpoint and hit
F5 instead of typing flags.

## CLI flags

| Flag | Default | Meaning |
|---|---|---|
| `--pictures` | *(required)* | Path to the pictures CSV (`take_at_min,size_mb,importance`) |
| `--passes` | *(required)* | Path to the passes CSV (`window_start_min,window_end_min,link_speed_mb_per_min`) |
| `--storage-mb` | `512` | Storage capacity in MB |
| `--storage-policy` | `value_density` | `importance_age` (baseline) or `value_density` (primary) |
| `--downlink-policy` | `density_fractional` | `importance_first` (baseline) or `density_fractional` (primary) |
| `--quiet` | off | Print only the summary block (for building a comparison table) |
| `--dump-events` | off | Debug aid: print every raw internal event. Not the report below - see `docs/NOTES.md` |

## The four policy combinations

Two independent interfaces, two implementations each, chosen by CLI flag and
constructed in `main.py` - the simulation engine never imports a concrete policy
class.

- **`--storage-policy importance_age`** - baseline. When a new picture doesn't fit,
  evict the lowest-importance residents first, oldest first within a level, until it
  fits. No check on whether the trade is worth it.
- **`--storage-policy value_density`** - primary, GDS-derived. Evict the
  lowest-value-density residents first until the incoming picture fits, but only
  admit if the incoming picture's value exceeds the summed value of everything
  evicted to make room. Otherwise skip and leave storage untouched.
- **`--downlink-policy importance_first`** - baseline. Send highest-importance
  pictures first, whole or not at all; a picture that doesn't fit entirely in the
  remaining per-minute budget is skipped this window.
- **`--downlink-policy density_fractional`** - primary. Fractional knapsack by value
  density: fill the budget with the densest pictures first, splitting the boundary
  picture across this window and the next.

Running all four combinations with `--quiet` against the provided data produces a
comparison table for "total value delivered" (what the policies actually optimize).
Each row is the `total value delivered` line from that combination's summary block -
the sum of `value_of(picture)` (high=100/medium=50/low=20) over every picture that
reached `SEND_COMPLETE`, i.e. was fully received on the ground, not just started:

| storage | downlink | total value delivered |
|---|---|---|
| importance_age | importance_first | 1010 |
| importance_age | density_fractional | 1110 |
| value_density | importance_first | 1070 |
| **value_density** | **density_fractional** | **1270** |

Each primary policy improves on its baseline counterpart individually, and the two
primaries together deliver the most value - a real result, not a cosmetic one.

## Watching it run live

The real data exercises both of the interesting failure modes unprompted, with the
default policies and no special flags - visible directly in
`python main.py --pictures pictures.csv --passes passes.csv`'s timeline:

- **Storage fills before the first window even opens.** By minute 20, storage is at
  500/512 MB. At minute 21, a 40MB `low`-importance picture arrives and is skipped -
  `value 20 does not exceed eviction-set value 50` - four minutes before the first
  pass opens at minute 25.
- **Both windows exhaust their budget mid-picture.** In window 1 (`[25,30)`), e.g.
  picture #07 starts sending at minute 26 (56 of 121 MB) and completes at minute 27
  (the remaining 65 MB) - a real chunk-and-resume, not a hypothetical one. Window 2
  (`[70,75)`) is saturated almost every tick: #24 spans minutes 70→71, #23 spans
  71→72, #12 spans 72→73, each carrying a remainder into the next minute because that
  minute's budget ran out first.

## Decisions and tradeoffs

**Half-open pass windows.** A pass is `[start_min, end_min)`: capacity is
`(end_min - start_min) * speed_mb_per_min`, which only holds if the interval is
half-open. A picture taken at exactly `window_end` is *not* sendable in that window
(it's already closed); a picture taken at exactly `window_start` *is* sendable that
same minute. The provided data exercises this boundary six times, and one picture
(`take_at_min == 75`, the last window's `end_min`) is unreachable specifically
because of it - see the "Unreachable" section of the report.

**Arrivals before transmission, within the same minute.** Each simulated minute
processes every arrival first, then that minute's transmission. This is what makes
a picture taken at `window_start` sendable immediately, but it also means an arrival
cannot benefit from space freed by a picture completing its send *in that same
minute* - the admission decision is made against the storage state before that
minute's downlink runs. That ordering is fixed and deliberate, not a bug.

**No floats for value density.** Value density is a ratio (`value / size_mb`), and
float ratios are where determinism quietly dies. Every density comparison uses
`fractions.Fraction(value, size_mb)` instead - exact rational arithmetic, no rounding,
reads as plainly as `value / size_mb` would. Every sort that touches density is a
total order, with each picture's original CSV row index as the final, unique
tie-breaker.

**No quoted-CSV support.** Parsing uses `csv.DictReader` with plain comma-splitting
semantics. A data value containing a comma would be misread as an extra column.
Not handled; documented here instead, per `CLAUDE.md`'s scope discipline.

**The omitted GDS `L` term.** `ValueDensityStorage` is derived from Greedy-Dual-Size
(GDS), ranking residents by value density and evicting the cheapest until the
incoming picture fits. Classic GDS also carries an inflation term `L` that rises
every time something is evicted, so a page evicted long ago and re-requested later
isn't unfairly cheap next to pages evicted more recently - it compensates for
*repeated access* to the same item over time. Every picture here is written once by
the camera and read once by the ground station; there's no repeated access for `L`
to correct for. Carrying it anyway would let a picture that's simply been sitting in
storage the longest accumulate enough inflated "credit" to eventually outrank a
freshly-arrived high-importance picture on density alone. Omitted deliberately - see
the class docstring in `satsim/policies/storage_policy.py`.

**Chunking with resume.** A picture tracks `sent_mb` and only leaves storage once
`sent_mb == size_mb`. A partially-sent picture survives to the next window and
resumes from its offset. This is also why `DensityFractionalDownlink`'s greedy
fractional fill is optimal for *delivered* value at all: without resume, a picture
cut off mid-transmission that never gets to finish would be counted as delivered
value it never actually provided on the ground.

**Evicting a partially-sent picture.** A picture with `sent_mb > 0` has already spent
real, non-refundable transmission budget - discarding it now writes off bandwidth
already used, unlike discarding an untouched picture. `ValueDensityStorage` resolves
this by ranking every untouched resident ahead of every partially-sent one (each
group still ordered by density), so a partially-sent picture is only evicted if it's
the only candidate left.

## Future work

**Deliberately out of scope**, per `CLAUDE.md`: an offline MILP/CP-SAT solver for a
clairvoyant optimum, which would let the online policies' 1270-value result be stated
as "N% of optimal" instead of just "better than baseline."

**What I'd add next, given two more days:**

- **Progressive image quality layers**, so downlink stops being all-or-nothing per
  picture - a picture cut off mid-transmission could still deliver a usable
  low-resolution pass instead of nothing.
- **Multi-window lookahead**, reserving some of window 1's budget for high-value
  arrivals known to be coming before window 2 opens, rather than treating each
  window's allocation independently.

## Output

Without `--quiet`: a chronological timeline (one line per event), a summary block,
and an "Unreachable" section listing pictures still resident at the end of the run
and, separately, pictures taken after the last window closed (derived from the pass
list at runtime - never a hardcoded count). With `--quiet`: only the summary block.

See `docs/NOTES.md` for every simplification and limitation accepted along the way.

## AI disclosure

`docs/PLAN.md` and `CLAUDE.md` were authored by the user before this session, from
their own research into the problem. Claude Code then implemented `docs/PLAN.md`
phase by phase, one commit per phase, each reviewed and approved before the next
began; a few implementation bugs were introduced and self-caught along the way (see
below). See `docs/AI_NOTES.md` for the full account, including what was changed and
self-caught mistakes.
