"""OFAC Specially Designated Nationals list (sdnList XML).

Wire format notes that drive the parser:

* **The namespace is declared by the document, not by the parser.** The
  published schema uses ``http://tempuri.org/sdnList.xsd``, and a parser that
  hardcodes it works right up until it does not: OFAC's Sanctions List Service
  and the legacy ``treasury.gov/ofac/downloads`` path have not always agreed on
  whether the namespace is present at all. A hardcoded URI fails in the worst
  possible way — every path lookup silently returns nothing, so the file parses
  to zero entries and the differ reports the entire list as delisted. This
  adapter reads the namespace off the root element and qualifies its own paths
  with whatever the document actually declares, including the empty case.
  Discovered against the live endpoint; see `test_namespace_is_read_from_the_document`.
* ``publshInformation`` -- the misspelling is OFAC's, and is load-bearing --
  carries ``Publish_Date`` and ``Record_Count``. ``Record_Count`` is used as an
  independent reconciliation target: if the number of parsed entries does not
  equal the number OFAC declares, the parse is wrong, not the list.
* Individuals carry ``firstName``/``lastName``; entities and vessels carry
  ``lastName`` only, with ``firstName`` absent rather than empty. Treating a
  missing ``firstName`` as an individual with a blank given name is the
  standard way to end up with a list of entities typed as people.
* Alias ``category`` is ``strong`` or ``weak``. Weak aliases are published for
  investigative context and are explicitly not intended for automated
  screening; they are retained here but tagged, because the count of strong
  aliases is what actually moves a screening system's recall.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from regdelta.normalize import to_iso2
from regdelta.schema import Address, Identifier, Record, Snapshot
from regdelta.sources.base import ParseError, SourceAdapter

#: The namespace the published schema declares. Used only to report when the
#: document disagrees with it, never to build a path.
DOCUMENTED_NS = "http://tempuri.org/sdnList.xsd"

#: What the Sanctions List Service actually served, observed 2026-08-18:
#:
#:     <sdnList xmlns="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML">
#:       <publshInformation>
#:         <Publish_Date>08/18/2026</Publish_Date>
#:         <Record_Count>19202</Record_Count>
#:
#: Same element structure, different namespace. Recorded here as provenance,
#: not as a constant: hardcoding this URI would reproduce the original bug the
#: next time the endpoint moves.
OBSERVED_NS_2026_08 = (
    "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML"
)


def namespace_of(tag: str) -> str:
    """Extract the namespace URI from a qualified tag, or '' if unqualified."""
    if tag.startswith("{"):
        return tag[1 : tag.index("}")]
    return ""


def _qualify(namespace: str, path: str) -> str:
    """Qualify a slash-separated path of local names with `namespace`."""
    if not namespace:
        return path
    return "/".join(f"{{{namespace}}}{part}" for part in path.split("/"))


def _text(node: ET.Element | None, namespace: str, path: str, default: str = "") -> str:
    if node is None:
        return default
    found = node.find(_qualify(namespace, path))
    if found is None or found.text is None:
        return default
    return found.text.strip()


class OfacSdnAdapter(SourceAdapter):
    source = "ofac_sdn"
    key_stability = "stable"  # OFAC uid is never reassigned
    endpoint = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"

    def parse(self, payload: bytes, as_of: str) -> Snapshot:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ParseError(f"OFAC SDN XML is not well-formed: {exc}") from exc

        namespace = namespace_of(root.tag)
        local_root = root.tag.split("}")[-1]
        if local_root != "sdnList":
            raise ParseError(
                f"expected root <sdnList>, got <{local_root}>"
                + (f" in namespace {namespace}" if namespace else " with no namespace")
            )

        publication = root.find(_qualify(namespace, "publshInformation"))
        publish_date = _text(publication, namespace, "Publish_Date")
        declared_raw = _text(publication, namespace, "Record_Count")
        declared = int(declared_raw) if declared_raw.isdigit() else None

        entries = root.findall(_qualify(namespace, "sdnEntry"))
        if not entries:
            # Say what was actually seen. "Zero entries" on its own sends the
            # reader looking for an OFAC outage when the cause is a schema or
            # namespace change on a file that downloaded perfectly.
            children = sorted({c.tag.split("}")[-1] for c in root})
            raise ParseError(
                "OFAC SDN XML contained no <sdnEntry> elements. "
                f"Root <{local_root}> declares namespace "
                f"{namespace or '(none)'}; documented namespace is {DOCUMENTED_NS}. "
                f"Child elements present: {', '.join(children) or '(none)'}. "
                "This is a schema change, not an empty list."
            )

        records = [self._entry(e, namespace) for e in entries]
        return Snapshot.from_records(
            self.source, as_of, records, publish_date=publish_date, declared_count=declared
        )

    # -- helpers ----------------------------------------------------------

    def _entry(self, entry: ET.Element, ns: str) -> Record:
        uid = _text(entry, ns, "uid")
        if not uid:
            raise ParseError("sdnEntry without uid")

        first = _text(entry, ns, "firstName")
        last = _text(entry, ns, "lastName")
        name = f"{first} {last}".strip() if first else last

        sdn_type = _text(entry, ns, "sdnType").casefold() or "unknown"
        entity_type = {
            "individual": "individual",
            "entity": "entity",
            "vessel": "vessel",
            "aircraft": "aircraft",
        }.get(sdn_type, "unknown")

        programs = tuple(
            sorted(
                p.text.strip()
                for p in entry.findall(_qualify(ns, "programList/program"))
                if p.text and p.text.strip()
            )
        )

        aliases = tuple(
            sorted(
                {self._alias(a, ns) for a in entry.findall(_qualify(ns, "akaList/aka"))} - {""}
            )
        )
        addresses = tuple(
            sorted(
                (self._address(a, ns) for a in entry.findall(_qualify(ns, "addressList/address"))),
                key=lambda a: a.canonical(),
            )
        )
        identifiers = tuple(
            sorted(
                (self._identifier(i, ns) for i in entry.findall(_qualify(ns, "idList/id"))),
                key=lambda i: i.canonical(),
            )
        )
        nationalities = tuple(
            sorted(
                {
                    to_iso2(_text(n, ns, "country")) or _text(n, ns, "country")
                    for n in entry.findall(_qualify(ns, "nationalityList/nationality"))
                }
                - {""}
            )
        )

        return Record(
            key=f"ofac:{uid}",
            source=self.source,
            name=name,
            entity_type=entity_type,
            programs=programs,
            aliases=aliases,
            addresses=addresses,
            identifiers=identifiers,
            nationalities=nationalities,
            remarks=_text(entry, ns, "remarks"),
            source_url=f"https://sanctionssearch.ofac.treas.gov/Details.aspx?id={uid}",
        )

    @staticmethod
    def _alias(node: ET.Element, ns: str) -> str:
        first = _text(node, ns, "firstName")
        last = _text(node, ns, "lastName")
        whole = f"{first} {last}".strip() if first else last
        category = _text(node, ns, "category").casefold()
        # Weak aliases are tagged inline so the diff shows the strength of an
        # added alias without needing a second field.
        return f"{whole} [weak]" if category == "weak" and whole else whole

    @staticmethod
    def _address(node: ET.Element, ns: str) -> Address:
        street_parts = [
            _text(node, ns, "address1"),
            _text(node, ns, "address2"),
            _text(node, ns, "address3"),
        ]
        raw_country = _text(node, ns, "country")
        return Address(
            street=" ".join(p for p in street_parts if p),
            city=_text(node, ns, "city"),
            region=_text(node, ns, "stateOrProvince"),
            postal_code=_text(node, ns, "postalCode"),
            country=to_iso2(raw_country) or raw_country,
        )

    @staticmethod
    def _identifier(node: ET.Element, ns: str) -> Identifier:
        raw_country = _text(node, ns, "idCountry")
        return Identifier(
            id_type=_text(node, ns, "idType"),
            value=_text(node, ns, "idNumber"),
            country=to_iso2(raw_country) or raw_country,
        )
