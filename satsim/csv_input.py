"""Parsing and validation for pictures.csv and passes.csv.

Uses csv.DictReader. Quoted fields and embedded commas are not supported -
a data value containing a comma will be misread as an extra column. See
README for this limitation.
"""
import csv

from satsim.models import Importance, Picture, Pass

PICTURE_COLUMNS = ("take_at_min", "size_mb", "importance")
PASS_COLUMNS = ("window_start_min", "window_end_min", "link_speed_mb_per_min")

_IMPORTANCE_BY_NAME = {importance.value: importance for importance in Importance}


class InputError(Exception):
    """Raised with every collected validation error across both input files."""

    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


def load_input(pictures_path: str, passes_path: str) -> tuple[list[Picture], list[Pass]]:
    errors: list[str] = []
    pictures = _load_pictures(pictures_path, errors)
    passes = _load_passes(passes_path, errors)
    if errors:
        raise InputError(errors)
    return (
        sorted(pictures, key=lambda p: (p.take_at_min, p.index)),
        sorted(passes, key=lambda p: p.start_min),
    )


def _load_pictures(path: str, errors: list[str]) -> list[Picture]:
    pictures: list[Picture] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not _check_header(reader.fieldnames, PICTURE_COLUMNS, path, errors):
            return pictures
        for row_index, row in enumerate(reader, start=1):
            picture = _parse_picture_row(row, row_index, reader.line_num, path, errors)
            if picture is not None:
                pictures.append(picture)
    return pictures


def _load_passes(path: str, errors: list[str]) -> list[Pass]:
    parsed: list[tuple[int, Pass]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not _check_header(reader.fieldnames, PASS_COLUMNS, path, errors):
            return []
        for row in reader:
            line_no = reader.line_num
            window = _parse_pass_row(row, line_no, path, errors)
            if window is not None:
                parsed.append((line_no, window))
    _check_overlaps(parsed, path, errors)
    return [window for _, window in parsed]


def _check_header(fieldnames, expected: tuple[str, ...], path: str, errors: list[str]) -> bool:
    before = len(errors)
    if fieldnames is None:
        errors.append(f"{path}:1: empty file, expected header {','.join(expected)}")
        return False
    actual = tuple(name.strip() for name in fieldnames)
    missing = [column for column in expected if column not in actual]
    extra = [column for column in actual if column not in expected]
    if missing:
        errors.append(f"{path}:1: missing column(s): {', '.join(missing)}")
    if extra:
        errors.append(f"{path}:1: unexpected column(s): {', '.join(extra)}")
    return len(errors) == before


def _parse_int(raw: str | None, field_name: str, line_no: int, path: str, errors: list[str]) -> int | None:
    text = (raw or "").strip()
    try:
        return int(text)
    except ValueError:
        errors.append(f"{path}:{line_no}: {field_name} is not an integer: '{text}'")
        return None


def _parse_picture_row(row: dict, index: int, line_no: int, path: str, errors: list[str]) -> Picture | None:
    before = len(errors)

    take_at_min = _parse_int(row.get("take_at_min"), "take_at_min", line_no, path, errors)
    size_mb = _parse_int(row.get("size_mb"), "size_mb", line_no, path, errors)
    importance_raw = (row.get("importance") or "").strip()
    importance = _IMPORTANCE_BY_NAME.get(importance_raw.lower())
    if importance is None:
        errors.append(f"{path}:{line_no}: unrecognised importance '{importance_raw}'")

    if take_at_min is not None and take_at_min < 0:
        errors.append(f"{path}:{line_no}: take_at_min must be >= 0, got {take_at_min}")
    if size_mb is not None and size_mb <= 0:
        errors.append(f"{path}:{line_no}: size_mb must be > 0, got {size_mb}")

    if len(errors) > before:
        return None
    return Picture(index=index, take_at_min=take_at_min, size_mb=size_mb, importance=importance)


def _parse_pass_row(row: dict, line_no: int, path: str, errors: list[str]) -> Pass | None:
    before = len(errors)

    start_min = _parse_int(row.get("window_start_min"), "window_start_min", line_no, path, errors)
    end_min = _parse_int(row.get("window_end_min"), "window_end_min", line_no, path, errors)
    speed = _parse_int(row.get("link_speed_mb_per_min"), "link_speed_mb_per_min", line_no, path, errors)

    if start_min is not None and end_min is not None and end_min <= start_min:
        errors.append(
            f"{path}:{line_no}: window_end_min ({end_min}) must be greater than "
            f"window_start_min ({start_min})"
        )
    if speed is not None and speed <= 0:
        errors.append(f"{path}:{line_no}: link_speed_mb_per_min must be > 0, got {speed}")

    if len(errors) > before:
        return None
    return Pass(start_min=start_min, end_min=end_min, speed_mb_per_min=speed)


def _check_overlaps(parsed: list[tuple[int, Pass]], path: str, errors: list[str]) -> None:
    for i in range(len(parsed)):
        line_a, pass_a = parsed[i]
        for j in range(i + 1, len(parsed)):
            line_b, pass_b = parsed[j]
            if pass_a.start_min < pass_b.end_min and pass_b.start_min < pass_a.end_min:
                errors.append(
                    f"{path}:{line_b}: window [{pass_b.start_min},{pass_b.end_min}) overlaps "
                    f"{path}:{line_a}: window [{pass_a.start_min},{pass_a.end_min})"
                )
