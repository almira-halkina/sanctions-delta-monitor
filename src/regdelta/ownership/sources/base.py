from __future__ import annotations

import gzip
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from regdelta.ownership.graph import OwnershipEdge, OwnershipNode


@dataclass
class IngestResult:
    """What an ingest produced, and what it refused to produce.

    The counters are not decoration. A run that emits ten thousand edges and
    skips two hundred thousand records is telling you something about coverage
    that the edge count alone hides, and coverage is what bounds every derived
    finding downstream.
    """

    nodes: list[OwnershipNode] = field(default_factory=list)
    edges: list[OwnershipEdge] = field(default_factory=list)
    records_read: int = 0
    skipped: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def summary(self) -> str:
        skipped = ", ".join(f"{k} {v:,}" for k, v in sorted(self.skipped.items())) or "none"
        return (
            f"{self.records_read:,} records read, {len(self.edges):,} edges, "
            f"{len(self.nodes):,} nodes, skipped: {skipped}"
        )


class OwnershipSource(ABC):
    name: str
    #: Whether this source states how much of a company is held.
    provides_percentages: bool

    @abstractmethod
    def ingest(self, *paths: Path, limit: int | None = None) -> IngestResult: ...


def open_lines(path: Path) -> Iterator[str]:
    """Stream text lines from a plain, gzipped or zipped file.

    Streaming rather than reading is not an optimisation here. The PSC snapshot
    is several gigabytes and roughly twelve million records; loading it would
    make the ingest impossible on an ordinary laptop, which is the machine this
    has to run on.
    """
    suffix = path.suffix.casefold()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
            if not names:
                return
            with archive.open(names[0]) as handle:
                for raw in handle:
                    yield raw.decode("utf-8", errors="replace")
    elif suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            yield from handle
    else:
        with open(path, encoding="utf-8", errors="replace") as handle:
            yield from handle
