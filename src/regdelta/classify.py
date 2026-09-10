"""Delta classification.

A raw delta stream is not usable by an analyst. Two hundred amendments on a
Tuesday are indistinguishable from each other until they are labelled by what
kind of regulatory event produced them, which programme they belong to, and
which jurisdiction they touch.

The taxonomy below is the one that determines what an analyst does next:

* ``new_designation`` -- a party that was not on the list is now on it. Triage
  immediately; ownership tail unknown.
* ``delisting`` -- a party has come off. Time-critical in the opposite
  direction: continuing to block a delisted party is its own compliance
  failure, and the derived set has to be recomputed because a delisting can
  un-block an entire downstream subtree.
* ``re_designation`` -- same party, different programme. The name does not
  move but the legal basis does; blocking versus sectoral is the difference
  between "no dealings" and "no new debt over 14 days".
* ``alias_expansion`` -- new spellings. Pure recall change: rerun screening
  against historical transactions, because hits that did not fire last month
  will fire now.
* ``identifier_enrichment`` -- registration or tax numbers added. This is the
  delta that makes an entity joinable to a corporate register, and therefore
  the delta that unlocks ownership analysis on a party that previously had no
  tail.
* ``administrative`` -- address corrections, remark text, formatting. Log it,
  do not page anyone.

`priority` exists because the brief has to be readable in five minutes. It is a
deliberate, documented ranking, not a model score.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from regdelta.diff import ChangeType, Delta
from regdelta.normalize import HIGH_OPACITY_JURISDICTIONS, classify_program, country_name


class EventType(str, Enum):
    NEW_DESIGNATION = "new_designation"
    DELISTING = "delisting"
    RE_DESIGNATION = "re_designation"
    ALIAS_EXPANSION = "alias_expansion"
    IDENTIFIER_ENRICHMENT = "identifier_enrichment"
    ADMINISTRATIVE = "administrative"


#: Lower sorts first in the brief.
PRIORITY: dict[EventType, int] = {
    EventType.NEW_DESIGNATION: 0,
    EventType.DELISTING: 1,
    EventType.RE_DESIGNATION: 2,
    EventType.IDENTIFIER_ENRICHMENT: 3,
    EventType.ALIAS_EXPANSION: 4,
    EventType.ADMINISTRATIVE: 5,
}


@dataclass(frozen=True, slots=True)
class ClassifiedDelta:
    delta: Delta
    event_type: EventType
    authorities: tuple[str, ...]
    jurisdictions: tuple[str, ...]
    high_opacity: bool
    rationale: str

    @property
    def priority(self) -> int:
        return PRIORITY[self.event_type]

    @property
    def key(self) -> str:
        return self.delta.key

    @property
    def name(self) -> str:
        return self.delta.name

    def to_dict(self) -> dict:
        d = self.delta.to_dict()
        d.update(
            {
                "event_type": self.event_type.value,
                "authorities": list(self.authorities),
                "jurisdictions": list(self.jurisdictions),
                "jurisdiction_names": [country_name(j) for j in self.jurisdictions],
                "high_opacity": self.high_opacity,
                "rationale": self.rationale,
                "priority": self.priority,
            }
        )
        return d


def _event_type(delta: Delta) -> tuple[EventType, str]:
    if delta.change_type is ChangeType.ADDED:
        return EventType.NEW_DESIGNATION, "key absent from prior publication"
    if delta.change_type is ChangeType.REMOVED:
        return EventType.DELISTING, "key present in prior publication, absent now"

    changed = set(delta.changed_fields)

    if "programs" in changed:
        return (
            EventType.RE_DESIGNATION,
            "programme list changed; legal basis for the restriction has moved",
        )
    if "identifiers" in changed:
        return (
            EventType.IDENTIFIER_ENRICHMENT,
            "registration or tax identifiers added; entity is now joinable to a corporate register",
        )
    if changed & {"aliases", "name"}:
        return (
            EventType.ALIAS_EXPANSION,
            "name strings changed; screening recall differs from yesterday",
        )
    return EventType.ADMINISTRATIVE, f"non-screening fields changed: {', '.join(sorted(changed))}"


def classify(delta: Delta) -> ClassifiedDelta:
    event_type, rationale = _event_type(delta)

    record = delta.record or delta.previous
    programs = record.programs if record else ()
    authorities: list[str] = []
    jurisdictions: list[str] = []
    for program in programs:
        authority, jurisdiction = classify_program(program)
        if authority not in authorities:
            authorities.append(authority)
        if jurisdiction and jurisdiction not in jurisdictions:
            jurisdictions.append(jurisdiction)

    # Address and nationality jurisdictions matter independently of programme:
    # a party designated under a Russia programme but incorporated in the UAE
    # is a re-export risk, and that only shows up in the address.
    if record:
        for addr in record.addresses:
            if addr.country and addr.country not in jurisdictions:
                jurisdictions.append(addr.country)
        for nat in record.nationalities:
            if nat and nat not in jurisdictions:
                jurisdictions.append(nat)

    return ClassifiedDelta(
        delta=delta,
        event_type=event_type,
        authorities=tuple(authorities),
        jurisdictions=tuple(jurisdictions),
        high_opacity=any(j in HIGH_OPACITY_JURISDICTIONS for j in jurisdictions),
        rationale=rationale,
    )


def classify_all(deltas: list[Delta]) -> list[ClassifiedDelta]:
    return sorted(
        (classify(d) for d in deltas),
        key=lambda c: (c.priority, c.delta.source, c.name),
    )
