"""UK Companies House persons-with-significant-control snapshot.

Free, updated daily, and the only one of the two sources that states how much
of a company is held -- which is what lets a 50% threshold be tested at all.

Wire format
-----------

A ZIP containing one file that is *not* valid JSON: it is one JSON object per
line. Parsing it as a document fails; parsing it line by line works. Roughly
twelve million records, so it is streamed rather than read.

Each line::

    {"company_number": "12345678",
     "data": {"kind": "corporate-entity-person-with-significant-control",
              "name": "EXAMPLE HOLDINGS LIMITED",
              "natures_of_control": ["ownership-of-shares-50-to-75-percent",
                                     "voting-rights-50-to-75-percent"],
              "identification": {"registration_number": "09876543",
                                 "country_registered": "United Kingdom",
                                 "legal_form": "Private Limited Company"},
              "address": {...},
              "notified_on": "2016-04-06",
              "ceased_on": null}}

Three things drive the parser
-----------------------------

**A ceased PSC is not an owner.** Records carry ``ceased_on``, and the snapshot
retains them. Including a ceased holding would derive restrictions from a
relationship that has ended -- telling a customer to block a company on the
strength of a shareholding disposed of three years ago. They are dropped, and
counted, so the drop is visible rather than assumed.

**Statements are not people.** The file mixes PSC records with statement
records -- ``psc-statement`` kinds recording that a company has no PSC, or has
not yet identified one, or that the PSC's details are withheld. Those carry no
owner and must not become nodes. The "no PSC identified" statements are
analytically interesting on their own, as an opacity signal, but they are not
ownership edges.

**The band is the data.** ``natures_of_control`` gives a band, never a number,
and the same holding usually appears twice: once as share ownership and once as
voting rights. Taking the maximum across the bands rather than the sum is the
only defensible reading -- summing shares and votes for one holding
double-counts a single relationship into a threshold breach that does not
exist.

Identity
--------

Companies House gives the *company* a number and gives the PSC nothing durable.
Corporate PSCs usually carry ``identification.registration_number``, which is a
real identifier and is used when present. Individuals carry a name and a
redacted date of birth -- month and year only, the day is withheld -- so the
node id is composed from normalised name plus that partial date. Two different
people sharing a name and a birth month will collide. That is a known and
accepted limitation of the register itself, not something this parser can fix,
and it is why individual-derived findings deserve more scepticism than
corporate ones.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from regdelta.normalize import normalize_name, strip_legal_form, to_iso2
from regdelta.ownership.graph import OwnershipEdge, OwnershipNode
from regdelta.ownership.sources.base import IngestResult, OwnershipSource, open_lines

#: Bands, read at the floor of the band. "25% to 50%" is taken as 25%, so it
#: cannot trip a 50% threshold on its own. Reading the midpoint would invent a
#: restriction the filing does not evidence.
NATURE_TO_PERCENT: dict[str, float] = {
    "ownership-of-shares-25-to-50-percent": 25.0,
    "ownership-of-shares-50-to-75-percent": 50.0,
    "ownership-of-shares-75-to-100-percent": 75.0,
    "voting-rights-25-to-50-percent": 25.0,
    "voting-rights-50-to-75-percent": 50.0,
    "voting-rights-75-to-100-percent": 75.0,
    # The limited-liability-partnership and trust variants use the same bands
    # with a different prefix.
    "ownership-of-shares-25-to-50-percent-as-firm": 25.0,
    "ownership-of-shares-50-to-75-percent-as-firm": 50.0,
    "ownership-of-shares-75-to-100-percent-as-firm": 75.0,
    "ownership-of-shares-25-to-50-percent-as-trust": 25.0,
    "ownership-of-shares-50-to-75-percent-as-trust": 50.0,
    "ownership-of-shares-75-to-100-percent-as-trust": 75.0,
    "voting-rights-25-to-50-percent-as-firm": 25.0,
    "voting-rights-50-to-75-percent-as-firm": 50.0,
    "voting-rights-75-to-100-percent-as-firm": 75.0,
    "voting-rights-25-to-50-percent-as-trust": 25.0,
    "voting-rights-50-to-75-percent-as-trust": 50.0,
    "voting-rights-75-to-100-percent-as-trust": 75.0,
}

#: Natures of control that carry no percentage. Under the EU's control limb
#: these are sufficient on their own; under the US rules they are not.
NATURE_TO_CONTROL: dict[str, str] = {
    "right-to-appoint-and-remove-directors": "right-to-appoint-and-remove-directors",
    "right-to-appoint-and-remove-directors-as-firm": "right-to-appoint-and-remove-directors",
    "right-to-appoint-and-remove-directors-as-trust": "right-to-appoint-and-remove-directors",
    "right-to-appoint-and-remove-person": "right-to-appoint-and-remove-directors",
    "significant-influence-or-control": "significant-influence-or-control",
    "significant-influence-or-control-as-firm": "significant-influence-or-control",
    "significant-influence-or-control-as-trust": "significant-influence-or-control",
}

PSC_KINDS: frozenset[str] = frozenset(
    {
        "individual-person-with-significant-control",
        "corporate-entity-person-with-significant-control",
        "legal-person-person-with-significant-control",
        "super-secure-person-with-significant-control",
    }
)


def company_node_id(company_number: str) -> str:
    return f"gb-coh:{company_number.strip().upper()}"


def psc_node_id(data: dict) -> str:
    """A durable-ish id for the holder.

    Registration number where the register gives one. Otherwise a digest of the
    normalised name and the redacted date of birth, which is the most the
    register discloses.
    """
    identification = data.get("identification") or {}
    registration = (identification.get("registration_number") or "").strip()
    if registration:
        country = to_iso2(identification.get("country_registered") or "") or "XX"
        return f"psc-reg:{country}:{registration.upper()}"

    name = normalize_name(data.get("name") or "")
    dob = data.get("date_of_birth") or {}
    born = f"{dob.get('year', '')}-{dob.get('month', '')}"
    material = f"{name}|{born}"
    return "psc-name:" + hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


def _percent_and_control(natures: list[str]) -> tuple[float | None, tuple[str, ...]]:
    """Maximum band, not the sum.

    A single holding is normally filed twice, as shares and as votes. Summing
    them turns one 50-75% relationship into 100-150% and manufactures a
    threshold breach out of a filing convention.
    """
    percents = [NATURE_TO_PERCENT[n] for n in natures if n in NATURE_TO_PERCENT]
    controls = tuple(sorted({NATURE_TO_CONTROL[n] for n in natures if n in NATURE_TO_CONTROL}))
    return (max(percents) if percents else None), controls


class CompaniesHousePsc(OwnershipSource):
    name = "gb-companies-house-psc"
    provides_percentages = True
    #: http://download.companieshouse.gov.uk/en_pscdata.html
    download_page = "http://download.companieshouse.gov.uk/en_pscdata.html"

    def ingest(self, *paths: Path, limit: int | None = None) -> IngestResult:
        result = IngestResult()
        seen_nodes: dict[str, OwnershipNode] = {}

        for path in paths:
            for line in open_lines(path):
                line = line.strip()
                if not line:
                    continue
                if limit is not None and result.records_read >= limit:
                    break
                result.records_read += 1

                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    result.skip("unparseable line")
                    continue

                data = row.get("data") or {}
                kind = (data.get("kind") or "").strip()

                if kind not in PSC_KINDS:
                    # psc-statement records: "no PSC identified", "PSC details
                    # withheld", exemption notices. Real signals about opacity,
                    # but not owners.
                    result.skip(f"not a psc record: {kind or 'no kind'}")
                    continue

                if data.get("ceased_on") or data.get("ceased"):
                    result.skip("ceased holding")
                    continue

                company_number = (row.get("company_number") or "").strip()
                if not company_number:
                    result.skip("no company number")
                    continue

                percent, controls = _percent_and_control(list(data.get("natures_of_control") or []))
                if percent is None and not controls:
                    result.skip("no usable nature of control")
                    continue

                owner_id = psc_node_id(data)
                owned_id = company_node_id(company_number)

                identification = data.get("identification") or {}
                address = data.get("address") or {}
                owner_country = (
                    to_iso2(identification.get("country_registered") or "")
                    or to_iso2(data.get("nationality") or "")
                    or to_iso2(address.get("country") or "")
                )

                if owner_id not in seen_nodes:
                    seen_nodes[owner_id] = OwnershipNode(
                        entity_id=owner_id,
                        name=strip_legal_form(data.get("name") or "") and (data.get("name") or ""),
                        jurisdiction=owner_country,
                    )
                if owned_id not in seen_nodes:
                    seen_nodes[owned_id] = OwnershipNode(
                        entity_id=owned_id, name="", jurisdiction="GB"
                    )

                result.edges.append(
                    OwnershipEdge(
                        owner_id=owner_id,
                        owned_id=owned_id,
                        percent=percent,
                        control_indicators=controls,
                        source=self.name,
                        as_of=(data.get("notified_on") or "").strip(),
                    )
                )

        result.nodes = list(seen_nodes.values())
        return result
