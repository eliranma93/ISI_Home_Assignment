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

## Phase 5

- Tests use `tempfile`, `pathlib`, `io`, and `contextlib` in addition to `unittest`.
  `CLAUDE.md`'s "Modules used" list (`csv, dataclasses, enum, abc, argparse, typing,
  unittest`) is read as scoping the *shipped application* (`satsim/`, `main.py`,
  `debug_dump.py`), which stays within it - not test-only imports, since the plan's own
  test descriptions ("small synthetic CSV fixtures written to a temp directory")
  necessarily require `tempfile`.
- Tests 1-7 exercise the engine/storage/policies directly against synthetic CSV
  fixtures (via a shared `tests/helpers.py`); tests 8-10 go through `main.main()` with
  stdout/stderr captured, since "exit non-zero" and "clean run" are CLI-level
  contracts. Deliberate mix, not an inconsistency.
- Test 2/3's fixtures originally used a pass window ([20,30)) that fell *inside* the
  simulated run, so the picture left standing after the eviction decision then got
  legitimately sent away by that window before the assertions ran - failing for the
  wrong reason (delivery, not eviction). Fixed by moving the window to before both
  arrivals ([0,1)) so nothing can ever be transmitted, isolating the storage decision
  under test.

## Phase 6

- Nothing from `PLAN.md`'s "If scope must be reduced" list was cut: `--quiet` shipped
  in Phase 4, all 10 tests shipped in Phase 5, and both the `ImportanceThenAgeStorage`
  baseline and its interface shipped in Phase 3. No reductions were necessary.
- Cosmetic, not fixed: `EVICTED`/`SKIPPED` detail text built from `f"for #{index}"` in
  `engine.py` is not zero-padded (renders `for #9`, not `for #09`), while every other
  picture-index column in the timeline is zero-padded to two digits (`#09`). Noticed
  during the Phase 4 review; left as-is since fixing it means either parsing engine-
  recorded detail strings back into numbers in `report.py` (fragile) or having the
  engine format for display (violates "the engine records, it never prints").
- `AI_NOTES.md` was not maintained incrementally despite `CLAUDE.md`'s explicit
  instruction to append from the first commit - it sat empty through Phases 0-5 and
  was reconstructed at Phase 6 from git history and session context instead. Flagged
  to the user before writing it; see `AI_NOTES.md` itself for the full account and
  disclaimer. This is the one place this project didn't follow its own rules, and it's
  recorded here for that reason rather than smoothed over.

## Post-Phase-6 documentation reorganization

- `PLAN.md`, `NOTES.md`, and `AI_NOTES.md` moved into `docs/`, keeping only `CLAUDE.md`
  (auto-loaded by Claude Code from the project root every session) and `README.md`
  (the repo's landing page) at the top level. Root now shows only the program and the
  two docs a reviewer needs immediately; process/planning docs are one click away.

## Post-Phase-6 documentation consolidation

- `PRESENTATION.md` was removed. `PLAN.md`'s Phase 6 called for it as a separate file,
  but the assignment brief only asks for `README.md` - a second file answering
  essentially the same four questions was assessed as overhead. Its unique content
  (the live-run walkthrough, the partial-send eviction rationale, and the "what I'd
  add next" list) was folded into `README.md` under new "Watching it run live" and
  "Future work" sections, plus one new bullet under "Decisions and tradeoffs". Content
  that was already duplicated in `README.md` (the comparison table, the float-
  determinism explanation, the GDS `L`-term and quoted-CSV limitations) was dropped
  rather than kept in two places.

## Out-of-plan additions

- `--dump-events`: prints every raw `Event` record, one per line. Added outside the
  phase plan as a debug aid for reviewing the engine's output before Phase 4's real
  timeline report exists. Deliberately not the Phase 4 format (no fixed-width columns,
  no storage-level annotation, no importance/size lookup) - just a thin repr of the
  event log for sanity-checking. Moved to its own `debug_dump.py` at the repo root once
  it pushed `main.py` over the ~150-line module guideline - kept out of `satsim/` since
  it isn't part of `CLAUDE.md`'s fixed architecture.
- `tests/test_density_sort.py`: three unit tests added outside Phase 5's fixed list of
  10, testing `sorted_ascending_by_density` directly rather than through the full
  CSV-driven pipeline - ascending order, the row-index tie-break on equal density, and
  that the function doesn't mutate its input.
