"""Out-of-plan debug aid: print every raw Event record. See NOTES.md.

Deliberately separate from satsim/report.py, which is the real Phase 4
timeline - this is a lower-level view (every SEND_START/PROGRESS/COMPLETE
kept distinct, plus each picture's take_at_min) useful for verifying the
engine's tick-by-tick behavior, not for the presentation.
"""
from satsim.models import Event, EventKind, Picture

# (header label, width, alignment) - shared between the header row and every
# data row so columns line up. DETAIL is appended separately, unpadded.
DUMP_COLUMNS = [
    ("MINUTE", 10, "<"),
    ("EVENT", 14, "<"),
    ("PIC", 5, "<"),
    ("SIZE", 6, ">"),
    ("IMPORTANCE", 11, "<"),
    ("TAKEN@", 10, "<"),
    ("STORAGE", 10, "<"),
]


def _format_dump_row(values: list[str]) -> str:
    cells = [f"{value:{align}{width}}" for value, (_, width, align) in zip(values, DUMP_COLUMNS)]
    return " ".join(cells)


def print_dump_events(events: list[Event], pictures: list[Picture], capacity_mb: int) -> None:
    pictures_by_index = {picture.index: picture for picture in pictures}
    header_values = [name for name, _, _ in DUMP_COLUMNS]
    print(_format_dump_row(header_values) + " DETAIL")

    used_mb = 0
    for event in events:
        picture = pictures_by_index[event.picture_index]
        if event.kind == EventKind.STORED:
            used_mb += picture.size_mb
        elif event.kind in (EventKind.EVICTED, EventKind.SEND_COMPLETE):
            used_mb -= picture.size_mb
        row_values = [
            f"[min {event.minute:03d}]",
            event.kind.value,
            f"#{event.picture_index:02d}",
            f"{picture.size_mb}MB",
            picture.importance.value,
            f"taken@{picture.take_at_min:03d}",
            f"{used_mb}/{capacity_mb}MB",
        ]
        print(_format_dump_row(row_values) + " " + event.detail)
