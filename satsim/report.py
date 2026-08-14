"""Timeline and summary formatting. The engine only records events; this
module is what turns them into the console report a reviewer follows."""
from dataclasses import dataclass

from satsim.models import Event, EventKind, Pass, Picture
from satsim.policies.value import ValueFunction
from satsim.storage import Storage, StoredPicture

_SEND_KINDS = (EventKind.SEND_START, EventKind.SEND_PROGRESS, EventKind.SEND_COMPLETE)

_DISPLAY_KIND = {
    EventKind.TAKEN: "TAKEN",
    EventKind.STORED: "STORED",
    EventKind.SKIPPED: "SKIPPED",
    EventKind.EVICTED: "EVICTED",
    EventKind.SEND_START: "SENT",
    EventKind.SEND_PROGRESS: "SENT",
    EventKind.SEND_COMPLETE: "SENT",
}


def format_timeline(events: list[Event], pictures: list[Picture], storage: Storage) -> list[str]:
    """One line per event, chronological, fixed-width columns:
    [min 025] SENT      #12   43MB  high     storage 468/512
    [min 021] EVICTED   #03   64MB  low      storage 448/512   for #09
    """
    pictures_by_index = {picture.index: picture for picture in pictures}
    lines: list[str] = []
    used_mb = 0
    for event in events:
        picture = pictures_by_index[event.picture_index]
        if event.kind == EventKind.STORED:
            used_mb += picture.size_mb
        elif event.kind in (EventKind.EVICTED, EventKind.SEND_COMPLETE):
            used_mb -= picture.size_mb

        if event.kind in _SEND_KINDS:
            size_mb, note = int(event.detail), ""
        else:
            size_mb, note = picture.size_mb, event.detail

        minute_field = f"[min {event.minute:03d}] "
        kind_field = f"{_DISPLAY_KIND[event.kind]:<10}"
        pic_field = f"#{event.picture_index:02d}".ljust(6)
        size_field = f"{size_mb}MB".ljust(6)
        importance_field = f"{picture.importance.value:<9}"
        storage_field = f"storage {used_mb}/{storage.capacity_mb}"
        line = minute_field + kind_field + pic_field + size_field + importance_field + storage_field
        if note:
            line += f"   {note}"
        lines.append(line)
    return lines


@dataclass(frozen=True)
class Summary:
    taken: int
    stored: int
    skipped: int
    evicted: int
    fully_sent: int
    partially_sent: int
    total_sent_mb: int
    peak_storage_mb: int
    capacity_mb: int
    total_value_delivered: int


def build_summary(
    events: list[Event], pictures: list[Picture], storage: Storage, value_function: ValueFunction
) -> Summary:
    pictures_by_index = {picture.index: picture for picture in pictures}
    return Summary(
        taken=sum(1 for e in events if e.kind == EventKind.TAKEN),
        stored=sum(1 for e in events if e.kind == EventKind.STORED),
        skipped=sum(1 for e in events if e.kind == EventKind.SKIPPED),
        evicted=sum(1 for e in events if e.kind == EventKind.EVICTED),
        fully_sent=sum(1 for e in events if e.kind == EventKind.SEND_COMPLETE),
        partially_sent=sum(1 for stored in storage.all() if stored.sent_mb > 0),
        total_sent_mb=sum(int(e.detail) for e in events if e.kind in _SEND_KINDS),
        peak_storage_mb=storage.peak_used_mb,
        capacity_mb=storage.capacity_mb,
        total_value_delivered=sum(
            value_function.value_of(pictures_by_index[e.picture_index], e.minute)
            for e in events
            if e.kind == EventKind.SEND_COMPLETE
        ),
    )


def format_summary(summary: Summary) -> list[str]:
    return [
        "Summary:",
        f"  pictures taken:        {summary.taken}",
        f"  stored:                {summary.stored}",
        f"  skipped:               {summary.skipped}",
        f"  evicted:               {summary.evicted}",
        f"  fully sent:            {summary.fully_sent}",
        f"  partially sent:        {summary.partially_sent}",
        f"  total MB sent:         {summary.total_sent_mb}",
        f"  peak storage MB:       {summary.peak_storage_mb}/{summary.capacity_mb}",
        f"  total value delivered: {summary.total_value_delivered}",
    ]


def unreachable_report(
    pictures: list[Picture], passes: list[Pass], storage: Storage
) -> tuple[list[StoredPicture], list[Picture]]:
    """Two groups, derived from the pass list at runtime - never a hardcoded
    count: pictures still resident in storage at run end, and pictures taken
    after the last transmitting minute, which never had any window at all.
    The half-open convention means the last transmitting minute is
    max(pass.end_min) - 1, so a picture taken exactly at that end_min is
    already unreachable.
    """
    still_in_storage = sorted(storage.all(), key=lambda stored: stored.picture.index)

    if passes:
        last_transmitting_minute = max(window.end_min for window in passes) - 1
        never_sendable = [picture for picture in pictures if picture.take_at_min > last_transmitting_minute]
    else:
        never_sendable = list(pictures)

    return still_in_storage, never_sendable


def format_unreachable(still_in_storage: list[StoredPicture], never_sendable: list[Picture]) -> list[str]:
    lines = ["Unreachable:"]

    total_resident_mb = sum(stored.picture.size_mb for stored in still_in_storage)
    lines.append(f"  still in storage at end of run: {len(still_in_storage)} pictures, {total_resident_mb} MB")
    for stored in still_in_storage:
        picture = stored.picture
        state = "partially sent" if stored.sent_mb > 0 else "untouched"
        lines.append(
            f"    #{picture.index:02d}  {picture.size_mb}MB  {picture.importance.value:<6}  "
            f"taken@{picture.take_at_min:03d}  ({state})"
        )

    total_late_mb = sum(picture.size_mb for picture in never_sendable)
    lines.append(f"  taken after the last window closed: {len(never_sendable)} pictures, {total_late_mb} MB")
    for picture in never_sendable:
        lines.append(
            f"    #{picture.index:02d}  {picture.size_mb}MB  {picture.importance.value:<6}  "
            f"taken@{picture.take_at_min:03d}"
        )

    return lines
