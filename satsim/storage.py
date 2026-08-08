"""Storage: holds pictures currently resident in memory, tracks capacity usage."""
from dataclasses import dataclass

from satsim.models import Picture


@dataclass
class StoredPicture:
    picture: Picture
    sent_mb: int = 0

    @property
    def remaining_mb(self) -> int:
        return self.picture.size_mb - self.sent_mb


class Storage:
    """Occupied space is charged at full picture size on arrival and released only
    when the picture is fully sent or evicted - a partially sent picture still
    occupies its whole size until sent_mb == size_mb."""

    def __init__(self, capacity_mb: int):
        self.capacity_mb = capacity_mb
        self.used_mb = 0
        self.peak_used_mb = 0
        self._pictures: dict[int, StoredPicture] = {}

    def __contains__(self, index: int) -> bool:
        return index in self._pictures

    def get(self, index: int) -> StoredPicture | None:
        return self._pictures.get(index)

    def all(self) -> list[StoredPicture]:
        return list(self._pictures.values())

    def free_mb(self) -> int:
        return self.capacity_mb - self.used_mb

    def add(self, picture: Picture) -> None:
        self._pictures[picture.index] = StoredPicture(picture=picture)
        self.used_mb += picture.size_mb
        self.peak_used_mb = max(self.peak_used_mb, self.used_mb)

    def remove(self, index: int) -> StoredPicture:
        stored = self._pictures.pop(index)
        self.used_mb -= stored.picture.size_mb
        return stored
