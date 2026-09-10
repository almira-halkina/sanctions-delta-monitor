"""Joining designated parties to nodes in the ownership graph.

This is the most dangerous step in the package, and it is worth being explicit
about why.

Everywhere else, an error produces a wrong number. Here, an error produces an
assertion that a **named real company is controlled by a sanctioned party**.
That is not a data-quality issue, it is a defamatory claim, and it is
actionable in a way that an incorrect count is not. A false negative here means
a gap in coverage that the reconciliation checks already report. A false
positive means telling a customer to stop trading with a company that has done
nothing wrong.

So the matcher is deliberately conservative, and the asymmetry is encoded
rather than left to judgement:

* Matches are **tiered**, and only the top two tiers seed the closure.
* Every match carries the evidence that produced it, so a finding can be
  audited back to the field that justified it.
* Weak matches are not discarded -- they go to a review queue, because a
  sanctioned party hiding behind a transliteration variant is exactly the case
  worth investigating. They just do not silently become findings.

Tiers
-----

``identifier``
    A shared identifier: an LEI carried in OFAC's ``idList``, or a company
    registration number that matches a Companies House node. Two parties with
    the same registration number in the same jurisdiction are the same party.
    Seeds the closure.

``name_and_country``
    Normalised names match after legal-form stripping, *and* the jurisdictions
    agree. "OOO Titan Logistika" and "Titan Logistika LLC", both in Russia.
    Seeds the closure.

``name_only``
    Names match, jurisdictions do not or one is unknown. Reviewed, not seeded.
    Company names are not unique across borders; "Alpha Trading Limited" exists
    in a dozen registers.

``transliteration``
    Only the aggressively folded transliteration keys agree -- ``Yevgeniy
    Zhuravlyov`` and ``Evgenii Juravlev``. Reviewed, never seeded. That folding
    is a recall device with known collisions; it is built to surface candidates
    for a human, not to assert identity.

Why not a scored model
----------------------

A record-linkage model with a tuned threshold would do better on recall, and
the companion entity-resolution project implements exactly that. It is not used
here because this step has no labelled ground truth on which to tune a
threshold, and an untuned score is a confidence number with nothing behind it.
Deterministic tiers can at least be explained to the person whose company was
matched.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from regdelta.normalize import strip_legal_form, transliteration_key
from regdelta.ownership.graph import OwnershipGraph
from regdelta.schema import Record

#: Identifier types that name a company uniquely enough to join on.
JOINABLE_ID_TYPES: tuple[str, ...] = (
    "legal entity number",
    "legal entity identifier",
    "lei",
    "registration number",
    "company number",
    "business registration",
    "commercial registry",
)


class Tier(str, Enum):
    IDENTIFIER = "identifier"
    NAME_AND_COUNTRY = "name_and_country"
    NAME_ONLY = "name_only"
    TRANSLITERATION = "transliteration"


#: Only these seed the ownership closure. Everything else is a review queue.
SEEDING_TIERS: frozenset[Tier] = frozenset({Tier.IDENTIFIER, Tier.NAME_AND_COUNTRY})


@dataclass(frozen=True, slots=True)
class Link:
    record_key: str
    record_name: str
    entity_id: str
    tier: Tier
    evidence: str

    @property
    def seeds_closure(self) -> bool:
        return self.tier in SEEDING_TIERS

    def to_dict(self) -> dict:
        return {
            "record_key": self.record_key,
            "record_name": self.record_name,
            "entity_id": self.entity_id,
            "tier": self.tier.value,
            "evidence": self.evidence,
            "seeds_closure": self.seeds_closure,
        }


@dataclass
class LinkSet:
    links: list[Link] = field(default_factory=list)

    @property
    def seeding(self) -> list[Link]:
        return [link for link in self.links if link.seeds_closure]

    @property
    def review(self) -> list[Link]:
        return [link for link in self.links if not link.seeds_closure]

    def by_tier(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for link in self.links:
            counts[link.tier.value] += 1
        return dict(counts)

    def list_keys_by_node(self) -> dict[str, set[str]]:
        """Sanctions keys to attach to each graph node, seeding tiers only."""
        out: dict[str, set[str]] = defaultdict(set)
        for link in self.seeding:
            out[link.entity_id].add(link.record_key)
        return dict(out)


def _normalised_ids(record: Record) -> set[tuple[str, str]]:
    """(id_type_family, value) pairs worth joining on."""
    out: set[tuple[str, str]] = set()
    for identifier in record.identifiers:
        kind = identifier.id_type.casefold()
        if not any(marker in kind for marker in JOINABLE_ID_TYPES):
            continue
        value = identifier.value.strip().upper().replace(" ", "")
        if not value:
            continue
        family = "lei" if "lei" in kind or "legal entity" in kind else "registration"
        out.add((family, value))
    return out


def _node_identifier_index(graph: OwnershipGraph) -> dict[tuple[str, str], str]:
    """Identifiers implied by the node id scheme itself.

    `lei:XXXX` carries an LEI; `gb-coh:12345678` and `psc-reg:GB:12345678`
    carry a registration number. Nothing is inferred that the id does not
    already state.
    """
    index: dict[tuple[str, str], str] = {}
    for node in graph:
        entity_id = node.entity_id
        if entity_id.startswith("lei:"):
            index[("lei", entity_id[4:].upper())] = entity_id
        elif entity_id.startswith("gb-coh:"):
            index[("registration", entity_id[7:].upper())] = entity_id
        elif entity_id.startswith("psc-reg:"):
            parts = entity_id.split(":")
            if len(parts) == 3:
                index[("registration", parts[2].upper())] = entity_id
    return index


def link_records(
    records: dict[str, Record],
    graph: OwnershipGraph,
) -> LinkSet:
    """Match designated parties to graph nodes, best tier per record."""
    id_index = _node_identifier_index(graph)

    name_index: dict[str, list[str]] = defaultdict(list)
    translit_index: dict[str, list[str]] = defaultdict(list)
    country_of: dict[str, str] = {}
    for node in graph:
        if not node.name:
            continue
        country_of[node.entity_id] = node.jurisdiction
        name_index[strip_legal_form(node.name)].append(node.entity_id)
        translit_index[transliteration_key(node.name)].append(node.entity_id)

    result = LinkSet()

    for key, record in records.items():
        best: Link | None = None

        # Tier 1: a shared identifier.
        for family, value in _normalised_ids(record):
            entity_id = id_index.get((family, value))
            if entity_id:
                best = Link(
                    record_key=key,
                    record_name=record.name,
                    entity_id=entity_id,
                    tier=Tier.IDENTIFIER,
                    evidence=f"{family} {value} present on both sides",
                )
                break

        record_countries = {a.country for a in record.addresses if a.country} | set(
            record.nationalities
        )

        if best is None:
            normalised = strip_legal_form(record.name)
            candidates = name_index.get(normalised, [])
            # A name matching many nodes is a generic name, not an identification.
            if candidates and len(candidates) == 1:
                entity_id = candidates[0]
                node_country = country_of.get(entity_id, "")
                if node_country and node_country in record_countries:
                    best = Link(
                        record_key=key,
                        record_name=record.name,
                        entity_id=entity_id,
                        tier=Tier.NAME_AND_COUNTRY,
                        evidence=f"name '{normalised}' and jurisdiction {node_country} agree",
                    )
                else:
                    best = Link(
                        record_key=key,
                        record_name=record.name,
                        entity_id=entity_id,
                        tier=Tier.NAME_ONLY,
                        evidence=(
                            f"name '{normalised}' agrees; jurisdiction "
                            f"{node_country or 'unknown'} vs "
                            f"{sorted(record_countries) or 'unknown'} does not"
                        ),
                    )
            elif len(candidates) > 1:
                # Ambiguous by construction. Recording it as a review item is
                # more useful than picking one and being right 1/n of the time.
                best = Link(
                    record_key=key,
                    record_name=record.name,
                    entity_id=candidates[0],
                    tier=Tier.NAME_ONLY,
                    evidence=f"name '{normalised}' matches {len(candidates)} nodes; ambiguous",
                )

        if best is None:
            folded = transliteration_key(record.name)
            candidates = translit_index.get(folded, [])
            if len(candidates) == 1:
                best = Link(
                    record_key=key,
                    record_name=record.name,
                    entity_id=candidates[0],
                    tier=Tier.TRANSLITERATION,
                    evidence=f"transliteration key '{folded}' agrees; spellings differ",
                )

        if best is not None:
            result.links.append(best)

    return result


def apply_links(graph: OwnershipGraph, links: LinkSet) -> OwnershipGraph:
    """Attach seeding links to their nodes as `list_keys`."""
    from regdelta.ownership.graph import OwnershipNode

    for entity_id, keys in links.list_keys_by_node().items():
        existing = graph.nodes.get(entity_id)
        if existing is None:
            continue
        graph.add_node(
            OwnershipNode(
                entity_id=entity_id,
                name=existing.name,
                jurisdiction=existing.jurisdiction,
                list_keys=tuple(sorted(set(existing.list_keys) | keys)),
            )
        )
    return graph
