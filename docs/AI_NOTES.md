# AI disclosure

## Disclaimer on how this file was written

`CLAUDE.md` states: *"Maintain `AI_NOTES.md` from the first commit — append as you go,
do not reconstruct it at the end."* That didn't happen — this file was created empty in
the Phase 0 commit and never updated through Phases 1–5. It was written now, at Phase 6,
reconstructed from git history (`git log`) and the session transcript, not from
contemporaneous notes. This is flagged directly in `NOTES.md` as a process failure, not
smoothed over. The account below is accurate to the best of that reconstruction, but it
is reconstruction, not a live log.

## Where AI was used

**Before this session (per the user's own `problems.txt`):** the user researched the
problem by hand for roughly two hours, then spent about 1.5 hours researching with
Claude, which led them to recognize this as a variant of an existing caching/eviction
problem (GDS-style value-density eviction) rather than something to solve from scratch.
`PLAN.md` and `CLAUDE.md` - the two documents this entire implementation follows - were
authored by the user before this session started, informed by that research.

**This session:** essentially all code in `satsim/`, `main.py`, `debug_dump.py`, and
`tests/` was written by Claude Code (Claude, Anthropic's CLI agent), executing
`PLAN.md` phase by phase under direct human review. For each phase: the agent read the
phase's spec, implemented it, ran it against the real data and/or a synthetic
fixture to verify the phase's stated acceptance criterion, reported what was built and
any limitation to the user, and waited for explicit go-ahead before starting the next
phase (this pacing was confirmed with the user via an explicit question before Phase 0
began, along with confirming git should be initialized and used for one commit per
phase).

Between the two update passes to `PLAN.md`, the user revised it independently (adding
the explicit "stop and report a contradiction, don't silently reconcile it" rule,
moving the three ABC definitions into Phase 2, and correcting the "unreachable
pictures" count from 7 pictures / 529 MB to the correct 8 pictures / 636 MB, per
half-open-window semantics). The agent verified that correction against the real CSV
data by hand before treating it as ground truth, rather than accepting the number on
faith - see the plan file recorded at the time for that reasoning.

## What was changed, and self-caught mistakes

Three implementation bugs were introduced by the agent and caught during its own
verification (not by the user), each documented at the time in `NOTES.md`:

1. **Phase 1** - `csv_input._check_header` originally returned `not errors` against
   the *shared, cross-file* error list rather than errors from that header check
   alone, so a bad `pictures.csv` would spuriously suppress all of `passes.csv`'s row
   validation. Caught by deliberately testing both files with errors at once, not just
   individually.
2. **Phase 4** - `report.format_timeline` chained an f-string literal directly into
   `.ljust(6)`; Python concatenates adjacent string literals before any method call
   binds, so the padding silently applied to the whole already-long line instead of
   one field, producing squashed output like `#0175MB`. Caught by running it against
   real data and reading the actual output rather than trusting the formatting code by
   inspection.
3. **Phase 5** - two eviction tests used a pass window that fell inside the simulated
   run, so the picture left standing after the eviction decision was later legitimately
   transmitted away before the assertion ran, failing for the wrong reason. Caught by
   reading the failure trace rather than assuming the test fixture was inert.

Outside of phase work, mid-session user requests (adding `--dump-events`, then its
picture-detail columns, header, and alignment fix, then a total-sent summary line) were
implemented directly by the agent and are recorded as "out-of-plan additions" in
`NOTES.md`, including the decision to extract them into a separate `debug_dump.py` once
they pushed `main.py` past the module-size guideline.

## What a reviewer should know

This is a from-scratch AI implementation of a plan the user wrote themselves - the
design decisions (GDS-derived eviction, half-open windows, chunking-with-resume,
integer cross-multiplication for determinism) originate in the user's `PLAN.md`, not
from the agent. The agent's job was disciplined execution against that spec, including
pushing back where the spec and the data disagreed (see the unreachable-count
correction above) rather than silently reconciling. Per `CLAUDE.md`'s own framing -
*"the graded deliverable is a live presentation... optimize for something that can be
fully explained and modified live"* - the user presenting this should personally verify
they can explain every design decision in `README.md`'s "Decisions and tradeoffs"
section and both policy docstrings, not defer that understanding to this file.
