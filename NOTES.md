# Notes — simplifications and deliberate omissions

## Phase 0

- `main.py`'s stub print originally used an em-dash; switched to a plain hyphen because
  the Windows console mangles non-ASCII characters under its default codepage. All
  `print()` output will stay ASCII-only for the rest of the project.

## Phase 1

- CSV loading does not catch `FileNotFoundError` / permission errors on the input paths.
  A missing file surfaces as an unhandled Python traceback rather than a clean message.
  Not in `PLAN.md`'s validation checklist (which covers file *content*, not file
  *existence*); would add a one-line try/except around the `open()` calls in
  `csv_input.py` if this were taken further.
- Quoted CSV fields and embedded commas are not supported, per `PLAN.md` — a value
  containing a comma is misread as an extra column. To be documented in the README
  (Phase 6).

## Phase 3

- `ValueDensityStorage._eviction_candidates` ranks every not-yet-sent picture ahead of
  every partially-sent one (each group ordered by density ascending), so a picture with
  `sent_mb > 0` is only ever evicted if it is the only remaining candidate. Rationale: a
  partial send has already spent real, non-refundable transmission budget on that
  picture; discarding it now writes off bandwidth already used, whereas discarding an
  untouched picture writes off nothing sent so far.
- `ImportanceThenAgeStorage` (baseline) has no "is this worth it" admission check at
  all - it always evicts enough lowest-importance/oldest residents to fit the incoming
  picture, even if the incoming picture is worth less than what it displaces (confirmed
  in testing: it evicts a 75MB `medium` picture to make room for a 40MB `low` one).
  `ValueDensityStorage`'s explicit `admit only if value(incoming) > evicted value` gate
  is what actually fixes this - the baseline's naivety here is deliberate, per
  `PLAN.md`, and is a direct, presentable illustration of why the value-density policy
  is the improvement.

## Phase 4

- Line count is now ~830 across `satsim/` + `main.py`, above `CLAUDE.md`'s "roughly 500
  lines" estimate. Growth is driven by explicitly-required scope: two concrete classes
  per policy interface, CSV validation that collects every error with a line number
  (not just the first), and a reporting module covering timeline + summary + an
  unreachable section derived at runtime. Nothing here is speculative or unrequested;
  flagging the total for visibility, not proposing to cut anything.
- `report.py` sits at 148 lines, one line under the ~150 module guideline.

## Out-of-plan additions

- `--dump-events`: prints every raw `Event` record, one per line. Added outside the
  phase plan as a debug aid for reviewing the engine's output before Phase 4's real
  timeline report exists. Deliberately not the Phase 4 format (no fixed-width columns,
  no storage-level annotation, no importance/size lookup) - just a thin repr of the
  event log for sanity-checking. Moved to its own `debug_dump.py` at the repo root once
  it pushed `main.py` over the ~150-line module guideline - kept out of `satsim/` since
  it isn't part of `CLAUDE.md`'s fixed architecture.
