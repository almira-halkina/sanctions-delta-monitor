"""Ownership graph.

Edges come from corporate registers -- UK Companies House PSC filings, EU
business registers, OpenCorporates-style aggregations -- after the register
records have been resolved to canonical entities. Resolution is not done here;
this package consumes an already-resolved edge list, which is what the
companion entity-resolution pipeline emits.

Three properties of real ownership data shape the design:

**Percentages are often missing or banded.** Companies House PSC filings do not
report a number; they report a band ("25% to 50%", "over 50%", "over 75%").
Many jurisdictions report nothing at all. An edge therefore carries
``percent: float | None``, and a null is propagated as *unknown*, never as
zero. Silently treating unknown as zero is how a screening system concludes
that a wholly-owned subsidiary of a designated parent is clean.

**Cycles exist.** Circular and reciprocal shareholdings are common in exactly
the structures worth investigating. Any traversal here must terminate on a
cyclic graph, which is why the closure is a fixed-point iteration rather than a
recursive descent.

**Edges have provenance and a date.** Ownership as of a filing date is not
ownership today, and a restriction derived from a three-year-old filing should
be presented differently from one derived from last week's. Both are carried
so the brief can say which.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

#: Companies House PSC bands, mapped to the conservative (lowest) percentage
#: consistent with the band. Conservative in the direction of under-claiming
#: restriction: a band of "25% to 50%" is read as 25%, so it will not on its
#: own trip a 50% threshold. The alternative -- reading the midpoint -- invents
#: restrictions that cannot be evidenced from the filing.
PSC_BANDS: dict[str, float] = {
    "ownership-of-shares-25-to-50-percent": 25.0,
    "ownership-of-shares-50-to-75-percent": 50.0,
    "ownership-of-shares-75-to-100-percent": 75.0,
    "voting-rights-25-to-50-percent": 25.0,
    "voting-rights-50-to-75-percent": 50.0,
    "voting-rights-75-to-100-percent": 75.0,
}

#: Non-percentage control signals. The EU's ownership-or-control test can be
#: satisfied by these alone; the US 50 Percent Rule cannot.
#:
#: `accounting-consolidation` is here because GLEIF's relationship data states
#: that a parent fully consolidates a subsidiary's accounts, and consolidating
#: the financial statements is one of the indicia of control the Council Best
#: Practices list. It is emphatically not a percentage, and must never be
#: turned into one: to OFAC and BIS a consolidating parent with no stated stake
#: is an unrecorded holding, which is `INDETERMINATE`, not `RESTRICTED`.
CONTROL_INDICATORS: frozenset[str] = frozenset(
    {
        "right-to-appoint-and-remove-directors",
        "significant-influence-or-control",
        "board-majority",
        "golden-share",
        "management-agreement",
        "accounting-consolidation",
    }
)


@dataclass(frozen=True, slots=True)
class OwnershipNode:
    entity_id: str
    name: str = ""
    jurisdiction: str = ""
    #: Keys into the restricted-party snapshots, e.g. ("ofac:12345",).
    list_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OwnershipEdge:
    owner_id: str
    owned_id: str
    percent: float | None
    control_indicators: tuple[str, ...] = ()
    source: str = ""
    as_of: str = ""

    @property
    def is_unknown_percent(self) -> bool:
        return self.percent is None

    @property
    def confers_control(self) -> bool:
        return bool(set(self.control_indicators) & CONTROL_INDICATORS)

    def describe(self) -> str:
        pct = "unknown %" if self.percent is None else f"{self.percent:g}%"
        tail = f" [{', '.join(self.control_indicators)}]" if self.control_indicators else ""
        return f"{pct}{tail}"


@dataclass
class OwnershipGraph:
    nodes: dict[str, OwnershipNode] = field(default_factory=dict)
    #: owned_id -> edges pointing at it. The closure walks upward from an
    #: entity to its owners, so this is the index that matters.
    _incoming: dict[str, list[OwnershipEdge]] = field(default_factory=lambda: defaultdict(list))
    _outgoing: dict[str, list[OwnershipEdge]] = field(default_factory=lambda: defaultdict(list))

    # -- construction -----------------------------------------------------

    def add_node(self, node: OwnershipNode) -> None:
        existing = self.nodes.get(node.entity_id)
        if existing is None:
            self.nodes[node.entity_id] = node
            return
        # Merge rather than overwrite: an entity can be introduced by an edge
        # before its own row is read.
        self.nodes[node.entity_id] = OwnershipNode(
            entity_id=node.entity_id,
            name=node.name or existing.name,
            jurisdiction=node.jurisdiction or existing.jurisdiction,
            list_keys=tuple(sorted(set(existing.list_keys) | set(node.list_keys))),
        )

    def add_edge(self, edge: OwnershipEdge) -> None:
        for entity_id in (edge.owner_id, edge.owned_id):
            if entity_id not in self.nodes:
                self.add_node(OwnershipNode(entity_id=entity_id))
        self._incoming[edge.owned_id].append(edge)
        self._outgoing[edge.owner_id].append(edge)

    # -- access -----------------------------------------------------------

    def owners_of(self, entity_id: str) -> list[OwnershipEdge]:
        return self._incoming.get(entity_id, [])

    def holdings_of(self, entity_id: str) -> list[OwnershipEdge]:
        return self._outgoing.get(entity_id, [])

    def __len__(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self._incoming.values())

    def __iter__(self) -> Iterator[OwnershipNode]:
        return iter(self.nodes.values())

    # -- loading ----------------------------------------------------------

    @classmethod
    def from_rows(
        cls, node_rows: Iterable[dict[str, str]], edge_rows: Iterable[dict[str, str]]
    ) -> OwnershipGraph:
        graph = cls()
        for row in node_rows:
            graph.add_node(
                OwnershipNode(
                    entity_id=row["entity_id"].strip(),
                    name=(row.get("name") or "").strip(),
                    jurisdiction=(row.get("jurisdiction") or "").strip(),
                    list_keys=tuple(
                        sorted(k.strip() for k in (row.get("list_keys") or "").split("|") if k.strip())
                    ),
                )
            )
        for row in edge_rows:
            graph.add_edge(
                OwnershipEdge(
                    owner_id=row["owner_id"].strip(),
                    owned_id=row["owned_id"].strip(),
                    percent=_parse_percent(row.get("percent", ""), row.get("band", "")),
                    control_indicators=tuple(
                        sorted(
                            c.strip()
                            for c in (row.get("control_indicators") or "").split("|")
                            if c.strip()
                        )
                    ),
                    source=(row.get("source") or "").strip(),
                    as_of=(row.get("as_of") or "").strip(),
                )
            )
        return graph

    @classmethod
    def from_csv(cls, nodes_path: Path, edges_path: Path) -> OwnershipGraph:
        with open(nodes_path, newline="", encoding="utf-8") as fh:
            node_rows = list(csv.DictReader(fh))
        with open(edges_path, newline="", encoding="utf-8") as fh:
            edge_rows = list(csv.DictReader(fh))
        return cls.from_rows(node_rows, edge_rows)


def _parse_percent(raw: str, band: str) -> float | None:
    raw = (raw or "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    band = (band or "").strip()
    if band in PSC_BANDS:
        return PSC_BANDS[band]
    return None
