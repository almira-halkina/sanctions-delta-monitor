"""BIS restricted parties, via the trade.gov Consolidated Screening List.

The CSL is a convenience aggregation of eleven US restricted-party lists. This
adapter keeps only the BIS-administered ones -- Entity List, Military End User,
Unverified List, Denied Persons -- because OFAC content is taken from the
authoritative SDN XML instead. Pulling the same designation from two feeds and
diffing both produces duplicate deltas that an analyst then de-duplicates by
hand.

The reason this feed matters more than it used to: from 10 November 2026 the
Affiliates Rule extends Entity List and MEU licence requirements to any entity
50 percent or more owned, individually or in aggregate, by a listed party.
Commerce's own preamble states affiliates will not be added to the Entity List,
so the CSL will remain a complete record of *listed* parties and an incomplete
record of *restricted* parties. That gap is what
`regdelta.ownership.closure` computes.

Field census of the keyless bulk file, 2026-08-19, 25,942 records total
--------------------------------------------------------------------

The file interleaves records from every contributing list, and they do not
share a schema. Counting how many records carry each key at all:

    id, name, source          25,942   every record
    type, ids                 19,686   SDN-shaped records only
    nationalities             19,202   exactly the SDN count
    license_policy, title     22,692
    start_date                 5,247
    standard_order             5,086   Denied Persons only

So on BIS records there is **no `type` and no `ids` array**. Entity type and
structured identifiers are not published in the bulk file for these lists. They
*are* available from the keyed search API, which is the trade-off that makes
`TRADE_GOV_API_KEY` worth setting: the keyless file is complete on membership
and thinner on attributes.

That gap is reported as a gap. `entity_type` is set to ``not-published`` rather
than ``unknown``, because "we do not know" and "the publisher does not say" are
different facts and only one of them is a reason to go looking for a bug.

Keys
----

There is no `entity_number` in this file. The only per-record identifier is
`id`, a 56-hex-character digest that trade.gov generates rather than a
business identifier BIS assigns. If that digest is derived from record content
-- and its shape suggests it is -- then adding one alias changes the id, and a
differ keyed on it reports an amendment as a delisting plus a new designation.
For a change monitor that is the wrong failure: a delisting is the delta a
customer acts on immediately.

So the key is composed from the fields that identify the *party* rather than
describe it: the list it sits on, its normalised name, and its listing date.
Those survive the edits that happen most often -- aliases added, licence text
reworded, remarks expanded. They do not survive a name correction, which will
surface as a removal plus an addition; that is a rarer event and one worth an
analyst's attention anyway.

The publisher's digest is carried through as an identifier so it stays visible
in the diff. If it turns out to be content-derived, that shows up as identifier
churn on otherwise unchanged records -- which is the evidence needed to
confirm it.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from regdelta.normalize import normalize_name, to_iso2
from regdelta.schema import Address, Identifier, Record, Snapshot
from regdelta.sources.base import ParseError, SourceAdapter

BIS_SOURCE_MARKERS: tuple[tuple[str, str], ...] = (
    ("Entity List", "Entity List (EL)"),
    ("Military End User", "Military End User (MEU) List"),
    ("Unverified List", "Unverified List (UVL)"),
    ("Denied Persons", "Denied Persons List (DPL)"),
)

#: Set on every BIS record. Distinguishes "the publisher does not say" from
#: "we could not work it out", which are different problems with different
#: fixes.
NOT_PUBLISHED = "not-published"


def _bis_program(source_label: str) -> str | None:
    for marker, canonical in BIS_SOURCE_MARKERS:
        if marker.casefold() in source_label.casefold():
            return canonical
    return None


def stable_key(program: str, name: str, start_date: str) -> str:
    """Key from what identifies the party, not from what describes it.

    Deliberately excludes aliases, addresses, licence text and remarks. Those
    are the fields that change on a normal publication day, and a key that
    moves when they do turns every amendment into a delisting.
    """
    material = "|".join((program, normalize_name(name), start_date))
    return "bis:" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


class BisCslAdapter(SourceAdapter):
    source = "bis_csl"
    #: Keys are composed here, not taken from the publisher, so they are stable
    #: against attribute edits. They still move if BIS corrects a party's name.
    key_stability = "composed"
    endpoint = "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json"

    def parse(self, payload: bytes, as_of: str) -> Snapshot:
        try:
            doc = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ParseError(f"CSL payload is not valid JSON: {exc}") from exc

        # The bulk download is a bare object with `results`; the search API
        # wraps the same shape. Accept either rather than depending on which
        # endpoint answered.
        if isinstance(doc, list):
            results: Any = doc
            published = ""
        elif isinstance(doc, dict):
            results = doc.get("results")
            published = str(doc.get("date_of_last_update") or doc.get("date") or "")
        else:
            raise ParseError(f"CSL payload is a {type(doc).__name__}, not a list or object")

        if not isinstance(results, list):
            raise ParseError("CSL payload has no 'results' array")

        records: list[Record] = []
        seen: dict[str, int] = {}
        for item in results:
            program = _bis_program(str(item.get("source", "")))
            if program is None:
                continue  # non-BIS list; owned by another adapter
            record = self._record(item, program, seen)
            records.append(record)

        if not records:
            raise ParseError(
                "CSL payload contained no BIS-administered entries. "
                f"Sources present: {sorted({str(i.get('source', '')) for i in results})[:8]}"
            )

        return Snapshot.from_records(
            self.source,
            as_of,
            records,
            publish_date=published,
            # `total` counts all eleven lists, not the BIS subset, so it cannot
            # reconcile against what this adapter keeps.
            declared_count=None,
        )

    def _record(self, item: dict[str, Any], program: str, seen: dict[str, int]) -> Record:
        name = (item.get("name") or "").strip()
        if not name:
            raise ParseError(f"CSL entry without a name: id={item.get('id')!r}")

        start_date = (item.get("start_date") or "").strip()
        key = stable_key(program, name, start_date)

        # Two entries can share list, name and listing date -- the same party
        # listed at two addresses, most often. Suffix rather than collide:
        # silently dropping the second is data loss disguised as clean output.
        count = seen.get(key, 0)
        seen[key] = count + 1
        if count:
            key = f"{key}#{count + 1}"

        addresses = tuple(
            sorted(
                (
                    Address(
                        street=(a.get("address") or "").strip(),
                        city=(a.get("city") or "").strip(),
                        region=(a.get("state") or "").strip(),
                        postal_code=(a.get("postal_code") or "").strip(),
                        country=to_iso2(a.get("country") or ""),
                    )
                    for a in item.get("addresses") or []
                ),
                key=lambda a: a.canonical(),
            )
        )

        # The bulk file publishes no `ids` array for BIS lists. Where the keyed
        # search API is used instead, it does -- so read it if present rather
        # than assuming the thinner shape.
        identifiers = [
            Identifier(
                id_type=(i.get("type") or "").strip(),
                value=(i.get("number") or "").strip(),
                country=to_iso2(i.get("country") or ""),
            )
            for i in item.get("ids") or []
        ]
        # Carry the publisher's digest so it stays visible in the diff. If it is
        # content-derived, that shows up here as churn on otherwise unchanged
        # records -- the evidence needed to confirm it.
        publisher_id = (item.get("id") or "").strip()
        if publisher_id:
            identifiers.append(Identifier(id_type="CSL digest", value=publisher_id))

        fr_notice = (item.get("federal_register_notice") or "").strip()
        programs = (program,) + ((f"FR {fr_notice}",) if fr_notice else ())

        # `type` is absent from BIS records in the bulk file. Say which of the
        # two possible reasons applies.
        raw_type = item.get("type")
        if raw_type is None:
            entity_type = NOT_PUBLISHED
        else:
            entity_type = str(raw_type).strip().casefold() or NOT_PUBLISHED

        return Record(
            key=key,
            source=self.source,
            name=name,
            entity_type=entity_type,
            programs=programs,
            aliases=tuple(sorted({(a or "").strip() for a in item.get("alt_names") or []} - {""})),
            addresses=addresses,
            identifiers=tuple(sorted(identifiers, key=lambda i: i.canonical())),
            nationalities=tuple(sorted({a.country for a in addresses} - {""})),
            remarks=(item.get("remarks") or "").strip(),
            listing_date=start_date,
            license_requirement=(item.get("license_requirement") or "").strip(),
            source_url=(item.get("source_list_url") or "").strip(),
        )
