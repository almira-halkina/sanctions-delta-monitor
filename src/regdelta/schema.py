"""Canonical record schema.

Four regulators publish restricted-party data in four different shapes: OFAC
ships XML with a bespoke namespace, BIS content arrives through the trade.gov
Consolidated Screening List as JSON, the EU publishes an FSD 1.1 XML export,
and the Federal Register exposes a REST API of rulemaking documents. Nothing
about their field names, identifier schemes, or country encodings agrees.

Everything upstream is coerced into `Record` before the differ ever sees it, so
that a change is diffable across sources and a designation on one list can be
joined to an ownership edge sourced from another.

Two design decisions are load-bearing:

1. `key` is the *stable* identifier for change tracking, namespaced by source
   (`ofac:12345`). Regulators reuse display names and reassign nothing, so the
   publisher's own primary key is the only safe join. Where a source has no
   durable key (the EU reuses `logicalId` but renumbers on re-adoption) the
   adapter says so in `key_stability`, and the differ downgrades its confidence
   in "removed" verdicts for that source accordingly.

2. Multi-valued fields (aliases, addresses, identifiers, programs) are stored
   as sorted tuples, not lists. Sanctions lists are not order-stable between
   publications -- the same entry can come back with its aliases permuted.
   Sorting at parse time is what stops a cosmetic reordering from being
   reported to an analyst as a substantive amendment.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SourceId = Literal["ofac_sdn", "bis_csl", "eu_fsd", "federal_register"]

#: Fields the differ compares. Anything not listed here is metadata that may
#: legitimately churn between publications (fetch timestamps, publication
#: counts) and must never surface as an entity-level amendment.
DIFFABLE_FIELDS: tuple[str, ...] = (
    "name",
    "entity_type",
    "programs",
    "aliases",
    "addresses",
    "identifiers",
    "nationalities",
    "remarks",
    "listing_date",
    "license_requirement",
)

#: Fields whose modification changes *who gets caught by a screening engine*
#: rather than merely describing an existing target. An alias addition is the
#: canonical example: entity count is unchanged, so a row-count reconciliation
#: reports a quiet day, while in fact every screening system in the world now
#: matches a string it did not match yesterday.
SCREENING_RELEVANT_FIELDS: frozenset[str] = frozenset(
    {"name", "aliases", "identifiers", "addresses"}
)


@dataclass(frozen=True, slots=True)
class Address:
    street: str = ""
    city: str = ""
    region: str = ""
    postal_code: str = ""
    country: str = ""

    def canonical(self) -> str:
        parts = [self.street, self.city, self.region, self.postal_code, self.country]
        return ", ".join(p for p in parts if p)


@dataclass(frozen=True, slots=True)
class Identifier:
    id_type: str = ""
    value: str = ""
    country: str = ""

    def canonical(self) -> str:
        tail = f" ({self.country})" if self.country else ""
        return f"{self.id_type}: {self.value}{tail}"


@dataclass(frozen=True, slots=True)
class Record:
    """One restricted party, normalised across regulators."""

    key: str
    source: SourceId
    name: str
    entity_type: str = "unknown"  # individual | entity | vessel | aircraft | unknown
    programs: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    addresses: tuple[Address, ...] = ()
    identifiers: tuple[Identifier, ...] = ()
    nationalities: tuple[str, ...] = ()
    remarks: str = ""
    listing_date: str = ""
    license_requirement: str = ""
    source_url: str = ""

    def diffable(self) -> dict[str, Any]:
        """Projection of this record onto the fields the differ compares."""
        out: dict[str, Any] = {}
        for name in DIFFABLE_FIELDS:
            value = getattr(self, name)
            if isinstance(value, tuple) and value and isinstance(value[0], (Address, Identifier)):
                out[name] = tuple(v.canonical() for v in value)
            else:
                out[name] = value
        return out

    def content_hash(self) -> str:
        """Stable hash of the diffable projection.

        Used as a fast-path equality test so that a 17,000-entry list can be
        compared field-by-field only for the handful of entries that moved.
        """
        payload = repr(sorted(self.diffable().items()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["addresses"] = [a.canonical() for a in self.addresses]
        d["identifiers"] = [i.canonical() for i in self.identifiers]
        d["programs"] = list(self.programs)
        d["aliases"] = list(self.aliases)
        d["nationalities"] = list(self.nationalities)
        return d


@dataclass(frozen=True, slots=True)
class RuleDocument:
    """A Federal Register document.

    Rulemaking is monitored on a different axis from designations: a rule can
    restrict thousands of parties without naming one of them. The Affiliates
    Rule is the standing example -- it added no entries to the Entity List and
    changed the restricted universe by an unknown but large multiple.
    """

    document_number: str
    title: str
    doc_type: str
    publication_date: str
    effective_on: str = ""
    agencies: tuple[str, ...] = ()
    cfr_parts: tuple[str, ...] = ()
    docket_ids: tuple[str, ...] = ()
    abstract: str = ""
    html_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Snapshot:
    """One source, as it stood on one day."""

    source: SourceId
    as_of: str
    records: dict[str, Record] = field(default_factory=dict)
    publish_date: str = ""
    declared_count: int | None = None

    @classmethod
    def from_records(
        cls,
        source: SourceId,
        as_of: str,
        records: Iterable[Record],
        publish_date: str = "",
        declared_count: int | None = None,
    ) -> Snapshot:
        by_key: dict[str, Record] = {}
        for rec in records:
            by_key[rec.key] = rec
        return cls(
            source=source,
            as_of=as_of,
            records=by_key,
            publish_date=publish_date,
            declared_count=declared_count,
        )

    def __len__(self) -> int:
        return len(self.records)
