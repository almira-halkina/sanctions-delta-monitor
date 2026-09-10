"""EU Consolidated Financial Sanctions List (FSD 1.1 XML export).

Included because the EU is where the ownership question diverges most sharply
from the US. OFAC's 50 Percent Rule blocks at fifty percent or more; the EU's
guidance treats *more than* 50% as ownership and adds a separate, qualitative
control test that no percentage can capture. Running one graph through both
regimes and getting two different derived sets is the point of
`regdelta.ownership.closure` -- and is the sort of divergence a multinational's
compliance team has to reconcile every time it screens a counterparty.

Wire format notes:

* Namespaced under ``http://eu.europa.ec/fpi/fsd/export``.
* One ``sanctionEntity`` carries many ``nameAlias`` children, one per language
  variant. The primary name is not flagged; convention is that the first
  English-language alias with a ``wholeName`` is the display name. Everything
  else is an alias -- which is why EU entries carry far more aliases than OFAC
  ones and why alias-count reconciliation has to be per-source.
* ``subjectType/@classificationCode`` is ``P`` for person, ``E`` for enterprise.
* ``logicalId`` is reused when an entity is re-adopted under a new regulation,
  so it is not safe as a delisting signal on its own.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from regdelta.normalize import to_iso2
from regdelta.schema import Address, Identifier, Record, Snapshot
from regdelta.sources.base import ParseError, SourceAdapter

NS = {"e": "http://eu.europa.ec/fpi/fsd/export"}


class EuFsdAdapter(SourceAdapter):
    source = "eu_fsd"
    key_stability = "unstable"  # logicalId is reused on re-adoption
    endpoint = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"

    def parse(self, payload: bytes, as_of: str) -> Snapshot:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ParseError(f"EU FSD XML is not well-formed: {exc}") from exc

        entities = root.findall("e:sanctionEntity", NS)
        if not entities:
            raise ParseError("EU FSD XML parsed to zero sanctionEntity elements")

        records = [self._entity(e) for e in entities]
        return Snapshot.from_records(
            self.source,
            as_of,
            records,
            publish_date=root.get("generationDate", ""),
            declared_count=len(entities),
        )

    def _entity(self, node: ET.Element) -> Record:
        logical_id = node.get("logicalId", "")
        eu_ref = node.get("euReferenceNumber", "")
        if not logical_id:
            raise ParseError("sanctionEntity without logicalId")

        classification = ""
        subject = node.find("e:subjectType", NS)
        if subject is not None:
            classification = subject.get("classificationCode", "")
        entity_type = {"P": "individual", "E": "entity"}.get(classification, "unknown")

        names: list[str] = []
        for alias in node.findall("e:nameAlias", NS):
            whole = (alias.get("wholeName") or "").strip()
            if not whole:
                first = (alias.get("firstName") or "").strip()
                last = (alias.get("lastName") or "").strip()
                whole = f"{first} {last}".strip()
            if whole:
                names.append(whole)

        display = names[0] if names else ""
        aliases = tuple(sorted(set(names[1:])))

        programmes = tuple(sorted({
            (r.get("programme") or "").strip()
            for r in node.findall("e:regulation", NS)
        } - {""}))

        addresses = tuple(sorted(
            (
                Address(
                    street=(a.get("street") or "").strip(),
                    city=(a.get("city") or "").strip(),
                    region=(a.get("region") or "").strip(),
                    postal_code=(a.get("zipCode") or "").strip(),
                    country=to_iso2(a.get("countryIso2Code") or a.get("countryDescription") or ""),
                )
                for a in node.findall("e:address", NS)
            ),
            key=lambda a: a.canonical(),
        ))

        identifiers = tuple(sorted(
            (
                Identifier(
                    id_type=(i.get("identificationTypeDescription") or "").strip(),
                    value=(i.get("number") or "").strip(),
                    country=to_iso2(i.get("countryIso2Code") or ""),
                )
                for i in node.findall("e:identification", NS)
            ),
            key=lambda i: i.canonical(),
        ))

        return Record(
            key=f"eu:{logical_id}",
            source=self.source,
            name=display,
            entity_type=entity_type,
            programs=programmes,
            aliases=aliases,
            addresses=addresses,
            identifiers=identifiers,
            nationalities=tuple(sorted({a.country for a in addresses} - {""})),
            remarks=(node.get("remark") or "").strip(),
            listing_date=node.get("designationDate", ""),
            source_url=f"https://data.europa.eu/euodp/en/data/dataset/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions#{eu_ref}",
        )
