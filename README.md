# Satellite Camera Data Manager

Simulates one orbit of a small satellite: pictures are taken on a fixed schedule,
stored in memory that's smaller than the data produced, and downlinked during two
short ground-station passes with limited bandwidth. Storage and link capacity are
**deliberately oversubscribed** - the interesting part is the keep / discard /
send-order decisions, not the plumbing.

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

## CLI flags

| Flag | Default | Meaning |
|---|---|---|
| `--pictures` | *(required)* | Path to the pictures CSV (`take_at_min,size_mb,importance`) |
| `--passes` | *(required)* | Path to the passes CSV (`window_start_min,window_end_min,link_speed_mb_per_min`) |
| `--storage-mb` | `512` | Storage capacity in MB |
| `--storage-policy` | `value_density` | `importance_age` (baseline) or `value_density` (primary) |
| `--downlink-policy` | `density_fractional` | `importance_first` (baseline) or `density_fractional` (primary) |
| `--quiet` | off | Print only the summary block (for building a comparison table) |
| `--dump-events` | off | Debug aid: print every raw internal event. Not the report below - see `NOTES.md` |

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
comparison table for "total value delivered" (what the policies actually optimize):

| storage | downlink | total value delivered |
|---|---|---|
| importance_age | importance_first | 1010 |
| importance_age | density_fractional | 1110 |
| value_density | importance_first | 1070 |
| **value_density** | **density_fractional** | **1270** |

Each primary policy improves on its baseline counterpart individually, and the two
primaries together deliver the most value - a real result, not a cosmetic one.

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
float ratios are where determinism quietly dies. Every density comparison is done
by integer cross-multiplication - `a.value * b.size_mb` vs `b.value * a.size_mb` -
never division. Every sort that touches density is a total order, with each
picture's original CSV row index as the final, unique tie-breaker.

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

## Output

Without `--quiet`: a chronological timeline (one line per event), a summary block,
and an "Unreachable" section listing pictures still resident at the end of the run
and, separately, pictures taken after the last window closed (derived from the pass
list at runtime - never a hardcoded count). With `--quiet`: only the summary block.

See `NOTES.md` for every simplification and limitation accepted along the way, and
`PRESENTATION.md` for the assignment's four required talking points.
