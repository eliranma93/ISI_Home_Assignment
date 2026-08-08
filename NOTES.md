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
