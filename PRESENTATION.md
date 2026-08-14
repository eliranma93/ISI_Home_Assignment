# Presentation notes

Answers to the four questions the assignment brief requires, grounded in this
implementation and the real provided data. See `README.md` for the "Decisions and
tradeoffs" section referenced below, and the two policy-class docstrings in
`satsim/policies/storage_policy.py` / `downlink_policy.py` for the full reasoning.

## 1. Design, and why - especially discard and send-order

Three interfaces, `abc.ABC` with `@abstractmethod`: `ValueFunction`, `StoragePolicy`,
`DownlinkPolicy`. Both `StoragePolicy` and `DownlinkPolicy` take a `ValueFunction` as a
constructor dependency, so eviction and transmission always rank pictures on the same
scale - `ImportanceValue` scores `HIGH=100 / MEDIUM=50 / LOW=20`.

- **Discard (`StoragePolicy`).** The baseline, `ImportanceThenAgeStorage`, evicts
  lowest-importance-then-oldest residents until the incoming picture fits - with no
  check on whether that trade is worth it. The primary, `ValueDensityStorage`, is
  derived from Greedy-Dual-Size: rank residents by value density ascending, accumulate
  eviction candidates until the incoming picture fits, and admit only if the incoming
  picture's value exceeds the summed value of everything evicted. That admission gate
  is the entire difference, and it's demonstrable: in testing, the baseline evicts a
  75MB `medium` picture to make room for a 40MB `low` one; the primary refuses that
  trade outright.
- **Send-order (`DownlinkPolicy`).** The baseline, `ImportanceFirstAtomic`, sends
  highest-importance-first, whole-or-nothing per window. The primary,
  `DensityFractionalDownlink`, is a fractional knapsack by value density descending,
  splitting the boundary picture across windows via chunking-with-resume.

The four-row comparison table (`--quiet`, all four combinations, real data):

| storage | downlink | total value delivered |
|---|---|---|
| importance_age | importance_first | 1010 |
| importance_age | density_fractional | 1110 |
| value_density | importance_first | 1070 |
| **value_density** | **density_fractional** | **1270** |

Each primary improves on its baseline counterpart independently, and the two
primaries together deliver the most value of any combination.

## 2. Run it live - storage filling, a window running out of time

The real data does both unprompted with the default policies:

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

Both are visible directly in `python main.py --pictures pictures.csv --passes passes.csv`'s
timeline, no special flags needed.

## 3. The trickiest part

Two candidates, both real:

- **Making density comparison deterministic without floats.** Value density is
  `value / size_mb`; comparing it as a float ratio is exactly where determinism
  quietly breaks (rounding, platform differences). Every comparison instead
  cross-multiplies - `a.value * b.size_mb` vs `b.value * a.size_mb` - and every sort
  that touches density carries the picture's original row index as a final, unique
  tie-breaker, so no two pictures ever compare equal. See
  `satsim/policies/value.py:sorted_ascending_by_density`, the single place both
  policies rank density, specifically so they can never drift onto different scales.
- **Whether a partially-sent picture may be evicted.** It already spent real,
  non-refundable transmission budget - discarding it writes off bandwidth already
  used, unlike discarding an untouched picture. `ValueDensityStorage` resolves this by
  ranking every untouched resident ahead of every partially-sent one (each group still
  ordered by density), so a partial send is only evicted if it's the only candidate
  left. Recorded in `NOTES.md`.

## 4. What I'd add with two more days, and what I deliberately left out

**Left out, deliberately:**
- The GDS aging term `L` - it exists to handle repeated access to the same item over
  time; every picture here is written once and read once, so there's nothing for it
  to correct for, and carrying it would let a stale picture accumulate enough inflated
  "credit" to outrank a fresh high-importance one.
- Quoted-CSV / embedded-comma support - `csv.DictReader` with plain comma semantics
  only; documented as a limitation rather than implemented.
- An offline optimal-benchmark solver (see below) - out of scope for this exercise on
  purpose, per `CLAUDE.md`.

**What I'd add next:**
- **An offline MILP/CP-SAT solver** to compute the clairvoyant optimum for the
  provided dataset, so the online policies' 1270-value result can be stated as "N% of
  optimal" instead of just "better than the baseline."
- **Progressive image quality layers**, so downlink stops being all-or-nothing per
  picture - a picture cut off mid-transmission could still deliver a usable
  low-resolution pass instead of nothing.
- **Multi-window lookahead**, reserving some of window 1's budget for high-value
  arrivals known to be coming before window 2 opens, rather than treating each
  window's allocation independently.
