"""GLEIF Level 2 relationship data -- "who owns whom", globally and free.

Legal entities holding an LEI are required to report their direct and ultimate
*accounting consolidating* parents. GLEIF publishes those relationships as the
RR-CDF concatenated file, and the entity names and countries behind the LEIs as
the LEI-CDF file. Both are free, unregistered downloads.

What it gives, and what it does not
-----------------------------------

It gives structure: which entity consolidates which, worldwide, for entities
inside the LEI system. It gives no percentages at all.

That has a specific and useful consequence for the three regimes. A
consolidating-parent edge carries no stake, so under the OFAC 50 Percent Rule
and the BIS Affiliates Rule it is an *unrecorded* holding by a restricted owner
-- which lands the subsidiary in `INDETERMINATE`, the research queue, rather
than in either column. Under the EU test it is different: consolidating the
subsidiary's financial statements is one of the indicia of control the Council
Best Practices list, and control alone is sufficient there.

So the same GLEIF edge produces "needs research" in Washington and "restricted"
in Brussels. That divergence is real, it is what a multinational's compliance
team actually has to reconcile, and it only becomes visible on real data.

Direct only, never ultimate
---------------------------

The file carries both ``IS_DIRECTLY_CONSOLIDATED_BY`` and
``IS_ULTIMATELY_CONSOLIDATED_BY``. Only the direct relationship becomes an
edge.

Loading both would be a double count. If A directly consolidates B and C
ultimately consolidates B, then adding both edges gives B two owners in the
aggregation step -- when in reality C's interest in B *runs through* A and is
the same interest, counted twice. The closure already derives the ultimate
relationship by iterating over the direct ones; that is what it is for.

The ultimate relationships are still read, and used as a consistency check: an
ultimate parent that the direct chain cannot reach means the direct graph has a
hole, and the check reports it rather than papering over it.

Wire format
-----------

CSV with dotted header names. Columns are matched on their trailing segment
rather than the full header string, because GLEIF has renamed prefixes between
format versions and a parser pinned to exact headers silently produces zero
rows -- the same failure mode as the OFAC namespace, with the same
consequences.

Relationship file, the columns that matter::

    Relationship.StartNode.NodeID          child LEI
    Relationship.EndNode.NodeID            parent LEI
    Relationship.RelationshipType          IS_DIRECTLY_CONSOLIDATED_BY, ...
    Relationship.RelationshipStatus        ACTIVE | INACTIVE
    Registration.RegistrationStatus        PUBLISHED | LAPSED | ...

LEI file::

    LEI
    Entity.LegalName
    Entity.LegalAddress.Country
    Entity.LegalJurisdiction
    Entity.EntityStatus                    ACTIVE | INACTIVE
"""

from __future__ import annotations

import csv
from pathlib import Path

from regdelta.normalize import to_iso2
from regdelta.ownership.graph import OwnershipEdge, OwnershipNode
from regdelta.ownership.sources.base import IngestResult, OwnershipSource, open_lines

DIRECT = "IS_DIRECTLY_CONSOLIDATED_BY"
ULTIMATE = "IS_ULTIMATELY_CONSOLIDATED_BY"

#: Accounting consolidation is one of the control indicia the EU Best Practices
#: list. It is not a percentage and must never be treated as one.
CONSOLIDATION_INDICATOR = "accounting-consolidation"

#: Relationship records that are not live should not create edges. A lapsed
#: registration is a relationship nobody is attesting to any more.
LIVE_RELATIONSHIP_STATUS = frozenset({"ACTIVE", ""})
LIVE_REGISTRATION_STATUS = frozenset({"PUBLISHED", "ACTIVE", ""})


def column_index(header: list[str], suffix: str) -> int | None:
    """Locate a column by its trailing dotted segment.

    Matching on the suffix rather than the whole header is deliberate. GLEIF
    has changed prefixes between format versions, and a parser pinned to exact
    header strings finds nothing and reports an empty file -- which reads as
    "no relationships published" rather than "we cannot read this".
    """
    target = suffix.casefold()
    for i, name in enumerate(header):
        if name.strip().casefold().endswith(target):
            return i
    return None


def _require(header: list[str], suffix: str, path: Path) -> int:
    index = column_index(header, suffix)
    if index is None:
        raise ValueError(
            f"{path.name}: no column ending in {suffix!r}. "
            f"Headers seen: {[h for h in header[:12]]}. "
            "This is a format change, not an empty file."
        )
    return index


class GleifLevel2(OwnershipSource):
    name = "gleif-level2"
    provides_percentages = False
    download_page = "https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file"

    def ingest(
        self,
        *paths: Path,
        limit: int | None = None,
        lei_path: Path | None = None,
    ) -> IngestResult:
        """`paths` are relationship files; `lei_path` is the optional Level 1 file."""
        result = IngestResult()
        names: dict[str, tuple[str, str]] = {}
        if lei_path is not None:
            names = self._read_names(lei_path, result)

        seen: dict[str, OwnershipNode] = {}
        ultimate: dict[str, str] = {}

        for path in paths:
            rows = csv.reader(open_lines(path))
            try:
                header = next(rows)
            except StopIteration:
                result.skip("empty file")
                continue

            i_child = _require(header, "startnode.nodeid", path)
            i_parent = _require(header, "endnode.nodeid", path)
            i_type = _require(header, "relationshiptype", path)
            i_rel_status = column_index(header, "relationshipstatus")
            i_reg_status = column_index(header, "registrationstatus")

            for row in rows:
                if limit is not None and result.records_read >= limit:
                    break
                result.records_read += 1
                if len(row) <= max(i_child, i_parent, i_type):
                    result.skip("short row")
                    continue

                rel_type = row[i_type].strip().upper()
                child = row[i_child].strip().upper()
                parent = row[i_parent].strip().upper()
                if not child or not parent:
                    result.skip("missing node id")
                    continue

                if (
                    i_rel_status is not None
                    and len(row) > i_rel_status
                    and row[i_rel_status].strip().upper() not in LIVE_RELATIONSHIP_STATUS
                ):
                    result.skip("relationship not active")
                    continue
                if (
                    i_reg_status is not None
                    and len(row) > i_reg_status
                    and row[i_reg_status].strip().upper() not in LIVE_REGISTRATION_STATUS
                ):
                    result.skip("registration not published")
                    continue

                if rel_type == ULTIMATE:
                    # Kept for the reachability check, never turned into an edge.
                    ultimate[child] = parent
                    result.skip("ultimate parent (used for validation, not as an edge)")
                    continue
                if rel_type != DIRECT:
                    # Branches, fund management, umbrella structures. Real
                    # relationships, but not ownership in the sense the 50%
                    # rules use.
                    result.skip(f"relationship type {rel_type}")
                    continue

                for lei in (child, parent):
                    if lei not in seen:
                        name, country = names.get(lei, ("", ""))
                        seen[lei] = OwnershipNode(
                            entity_id=f"lei:{lei}", name=name, jurisdiction=country
                        )

                result.edges.append(
                    OwnershipEdge(
                        owner_id=f"lei:{parent}",
                        owned_id=f"lei:{child}",
                        percent=None,  # GLEIF states no percentage. Never invent one.
                        control_indicators=(CONSOLIDATION_INDICATOR,),
                        source=self.name,
                        as_of="",
                    )
                )

        result.nodes = list(seen.values())
        self.unreachable_ultimates = self._check_reachability(result.edges, ultimate)
        if self.unreachable_ultimates:
            result.skip(
                f"ultimate parents not reachable through direct edges: "
                f"{len(self.unreachable_ultimates)}"
            )
        return result

    # -- helpers ----------------------------------------------------------

    def _read_names(self, path: Path, result: IngestResult) -> dict[str, tuple[str, str]]:
        rows = csv.reader(open_lines(path))
        try:
            header = next(rows)
        except StopIteration:
            result.skip("empty LEI file")
            return {}

        i_lei = _require(header, "lei", path)
        i_name = column_index(header, "legalname")
        i_country = column_index(header, "legaladdress.country") or column_index(
            header, "legaljurisdiction"
        )

        names: dict[str, tuple[str, str]] = {}
        for row in rows:
            if not row or len(row) <= i_lei:
                continue
            lei = row[i_lei].strip().upper()
            if not lei:
                continue
            name = row[i_name].strip() if i_name is not None and len(row) > i_name else ""
            country = (
                to_iso2(row[i_country].strip())
                if i_country is not None and len(row) > i_country
                else ""
            )
            names[lei] = (name, country)
        return names

    @staticmethod
    def _check_reachability(edges: list[OwnershipEdge], ultimate: dict[str, str]) -> list[str]:
        """Ultimate parents the direct chain cannot reach.

        GLEIF reports both, and they should agree: walking direct edges upward
        from a child ought to arrive at its declared ultimate parent. Where it
        does not, the direct graph has a hole -- a link nobody filed. Reporting
        the count is more honest than a graph that looks complete because the
        gaps are invisible.
        """
        parents: dict[str, str] = {e.owned_id: e.owner_id for e in edges}
        unreachable: list[str] = []
        for child, declared in ultimate.items():
            node, target = f"lei:{child}", f"lei:{declared}"
            hops = 0
            while node in parents and hops < 32:
                node = parents[node]
                hops += 1
                if node == target:
                    break
            else:
                unreachable.append(child)
                continue
            if node != target:
                unreachable.append(child)
        return unreachable
