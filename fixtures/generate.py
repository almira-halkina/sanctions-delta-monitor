#!/usr/bin/env python3
"""Deterministic fixture generator.

The fixtures in this repository are synthetic. No real person or company is
named, and nothing here should be read as an allegation about anyone. They are
generated rather than hand-written for three reasons:

* the wire formats are reproduced exactly, so the parsers are exercised against
  the same bytes shapes the regulators actually publish -- namespaced XML with
  OFAC's `publshInformation` misspelling intact, CSL JSON with its
  long-descriptive `source` labels, EU FSD 1.1 with one `nameAlias` per
  language;
* the corpus is large enough that the reconciliation thresholds are meaningful.
  Six changes against fourteen entries is 43% churn and would trip the ceiling
  every time; six against two hundred and fifty is the ~2% a real publication
  day looks like;
* it is regenerable, so a reviewer can change the scenario and re-run rather
  than editing XML by hand.

The scenario spans two publication days, 2026-08-03 and 2026-08-04, and is
built to produce one instance of every case the pipeline claims to handle.
See `docs/findings.md` for what each one demonstrates.

    python fixtures/generate.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent

# The ownership graph has to reference the same keys the adapters will produce.
# BIS keys are composed from list, name and listing date rather than taken from
# the publisher, so they are computed here with the adapter's own function.
# Hardcoding the digests would leave the fixture graph silently pointing at
# nothing the moment the key scheme changed -- and a graph with no seeds reports
# zero derived restrictions, which looks like a finding rather than a break.
sys.path.insert(0, str(HERE.parent / "src"))
from regdelta.sources.bis_csl import stable_key  # noqa: E402

DAY1, DAY2 = "2026-08-03", "2026-08-04"

# ---------------------------------------------------------------------------
# Story entries. Each exists to exercise one specific path.
# ---------------------------------------------------------------------------

VOLNA_UID = "47120"        # new designation on day 2 -> drives the whole closure
KARPENKA_UID = "31877"     # delisted on day 2 -> releases a downstream subtree
ZHURAVLYOV_UID = "22045"   # gains transliteration aliases -> recall change only
TITAN_UID = "19004"        # gains INN/OGRN -> becomes joinable to the register
SEVASTOPOL_UID = "28810"   # programme moves sectoral -> blocking
NEVSKY_UID = "20551"       # address correction -> administrative noise


def sdn_entry(
    uid: str,
    *,
    first: str = "",
    last: str,
    sdn_type: str,
    programs: list[str],
    akas: list[tuple[str, str, str]] | None = None,  # (first, last, category)
    addresses: list[dict[str, str]] | None = None,
    ids: list[dict[str, str]] | None = None,
    nationalities: list[str] | None = None,
    remarks: str = "",
) -> str:
    parts = ["  <sdnEntry>", f"    <uid>{uid}</uid>"]
    if first:
        parts.append(f"    <firstName>{first}</firstName>")
    parts.append(f"    <lastName>{last}</lastName>")
    parts.append(f"    <sdnType>{sdn_type}</sdnType>")
    if remarks:
        parts.append(f"    <remarks>{remarks}</remarks>")
    parts.append("    <programList>")
    for program in programs:
        parts.append(f"      <program>{program}</program>")
    parts.append("    </programList>")

    if ids:
        parts.append("    <idList>")
        for i, identifier in enumerate(ids, start=1):
            parts.append("      <id>")
            parts.append(f"        <uid>{uid}{i:02d}</uid>")
            parts.append(f"        <idType>{identifier['type']}</idType>")
            parts.append(f"        <idNumber>{identifier['number']}</idNumber>")
            if identifier.get("country"):
                parts.append(f"        <idCountry>{identifier['country']}</idCountry>")
            parts.append("      </id>")
        parts.append("    </idList>")

    if akas:
        parts.append("    <akaList>")
        for i, (aka_first, aka_last, category) in enumerate(akas, start=1):
            parts.append("      <aka>")
            parts.append(f"        <uid>{uid}{i:02d}</uid>")
            parts.append("        <type>a.k.a.</type>")
            parts.append(f"        <category>{category}</category>")
            if aka_first:
                parts.append(f"        <firstName>{aka_first}</firstName>")
            parts.append(f"        <lastName>{aka_last}</lastName>")
            parts.append("      </aka>")
        parts.append("    </akaList>")

    if addresses:
        parts.append("    <addressList>")
        for i, address in enumerate(addresses, start=1):
            parts.append("      <address>")
            parts.append(f"        <uid>{uid}{i:02d}</uid>")
            for tag, key in (
                ("address1", "address1"),
                ("city", "city"),
                ("stateOrProvince", "state"),
                ("postalCode", "postal"),
                ("country", "country"),
            ):
                if address.get(key):
                    parts.append(f"        <{tag}>{address[key]}</{tag}>")
            parts.append("      </address>")
        parts.append("    </addressList>")

    if nationalities:
        parts.append("    <nationalityList>")
        for i, country in enumerate(nationalities, start=1):
            parts.append("      <nationality>")
            parts.append(f"        <uid>{uid}{i:02d}</uid>")
            parts.append(f"        <country>{country}</country>")
            parts.append("      </nationality>")
        parts.append("    </nationalityList>")

    parts.append("  </sdnEntry>")
    return "\n".join(parts)


def filler_entries(count: int = 250) -> list[str]:
    """Background entries, identical on both days.

    Their only job is to make the churn ratio realistic, so the reconciliation
    thresholds in `regdelta.qa` are exercised against a plausible denominator
    rather than a toy one.
    """
    rng = random.Random(20260803)
    surnames = ["Abramyan", "Baranov", "Cherkasov", "Dorokhin", "Fedotov", "Golubev",
                "Ilyushin", "Kalinin", "Lebedev", "Morozov", "Nesterov", "Ostrovsky",
                "Panfilov", "Rozhkov", "Savchenko", "Tikhonov", "Ustinov", "Vlasov"]
    givens = ["Andrei", "Boris", "Dmitri", "Egor", "Grigori", "Ivan", "Konstantin",
              "Leonid", "Mikhail", "Nikolai", "Pavel", "Roman", "Sergei", "Timur"]
    forms = ["OOO", "AO", "PAO", "ZAO"]
    stems = ["Almaz", "Beryoza", "Vektor", "Granit", "Delta", "Zenit", "Iskra",
             "Kometa", "Luch", "Meteor", "Neva", "Orbita", "Priboi", "Rubin",
             "Sokol", "Topaz", "Uran", "Fakel", "Kholod", "Tsirkon"]
    cities = [("Moscow", "Russia"), ("St. Petersburg", "Russia"), ("Minsk", "Belarus"),
              ("Kazan", "Russia"), ("Yekaterinburg", "Russia"), ("Dubai", "United Arab Emirates"),
              ("Istanbul", "Turkey"), ("Almaty", "Kazakhstan"), ("Hong Kong", "Hong Kong")]
    programs = ["RUSSIA-EO14024", "BELARUS-EO14038", "UKRAINE-EO13662", "IRAN-EO13902",
                "DPRK4", "SDGT", "GLOMAG"]

    out: list[str] = []
    for n in range(count):
        uid = str(60000 + n)
        city, country = rng.choice(cities)
        if n % 3 == 0:
            first, last = rng.choice(givens), rng.choice(surnames)
            out.append(sdn_entry(
                uid, first=first, last=last, sdn_type="Individual",
                programs=[rng.choice(programs)],
                addresses=[{"city": city, "country": country}],
                nationalities=[country],
            ))
        else:
            last = f"{rng.choice(forms)} {rng.choice(stems)}"
            out.append(sdn_entry(
                uid, last=last, sdn_type="Entity",
                programs=[rng.choice(programs)],
                addresses=[{"address1": f"{rng.randint(1, 90)} Promyshlennaya Str.",
                            "city": city, "country": country}],
            ))
    return out


def build_sdn(day: str) -> str:
    entries: list[str] = []

    # -- delisting: present on day 1 only ---------------------------------
    if day == DAY1:
        entries.append(sdn_entry(
            KARPENKA_UID, first="Siarhei Ivanavich", last="Karpenka", sdn_type="Individual",
            programs=["BELARUS-EO14038"],
            akas=[("Sergey Ivanovich", "Karpenko", "strong")],
            addresses=[{"city": "Minsk", "country": "Belarus"}],
            nationalities=["Belarus"],
            remarks="SYNTHETIC TEST RECORD - not a real person.",
        ))

    # -- new designation: present on day 2 only ---------------------------
    if day == DAY2:
        entries.append(sdn_entry(
            VOLNA_UID, last="PUBLICHNOE AKTSIONERNOE OBSHCHESTVO VOLNA HOLDING",
            sdn_type="Entity",
            programs=["RUSSIA-EO14024"],
            akas=[("", "PAO VOLNA HOLDING", "strong"),
                  ("", "VOLNA HOLDING PJSC", "strong"),
                  ("", "VOLNA GROUP", "weak")],
            addresses=[{"address1": "14 Presnenskaya Naberezhnaya", "city": "Moscow",
                        "postal": "123112", "country": "Russia"}],
            ids=[{"type": "Tax ID No.", "number": "7736207543", "country": "Russia"},
                 {"type": "Registration Number", "number": "1027700070139", "country": "Russia"}],
            remarks="SYNTHETIC TEST RECORD - not a real company.",
        ))

    # -- alias expansion: same key, new transliterations on day 2 ---------
    zhuravlyov_akas = [("Evgeny", "Zhuravlev", "strong")]
    if day == DAY2:
        zhuravlyov_akas += [("Evgenii", "Juravlev", "strong"),
                            ("Yevgeniy", "Zhuravlyow", "weak")]
    entries.append(sdn_entry(
        ZHURAVLYOV_UID, first="Yevgeniy Petrovich", last="Zhuravlyov",
        sdn_type="Individual", programs=["RUSSIA-EO14024"], akas=zhuravlyov_akas,
        addresses=[{"city": "Moscow", "country": "Russia"}],
        nationalities=["Russia"],
        remarks="SYNTHETIC TEST RECORD - not a real person.",
    ))

    # -- identifier enrichment: registry numbers added on day 2 -----------
    titan_ids = [{"type": "Tax ID No.", "number": "7802873456", "country": "Russia"},
                 {"type": "Registration Number", "number": "1157847123456", "country": "Russia"}] \
        if day == DAY2 else []
    entries.append(sdn_entry(
        TITAN_UID, last="OBSHCHESTVO S OGRANICHENNOI OTVETSTVENNOSTYU TITAN LOGISTIKA",
        sdn_type="Entity", programs=["RUSSIA-EO14024"],
        akas=[("", "OOO TITAN LOGISTIKA", "strong"), ("", "TITAN LOGISTICS LLC", "strong")],
        addresses=[{"address1": "8 Sofiyskaya Str.", "city": "St. Petersburg", "country": "Russia"}],
        ids=titan_ids,
        remarks="SYNTHETIC TEST RECORD - not a real company.",
    ))

    # -- re-designation: sectoral on day 1, blocking on day 2 -------------
    entries.append(sdn_entry(
        SEVASTOPOL_UID, last="AKTSIONERNOE OBSHCHESTVO SEVASTOPOL MARINE ENGINEERING",
        sdn_type="Entity",
        programs=["UKRAINE-EO13662"] if day == DAY1 else ["RUSSIA-EO14024"],
        akas=[("", "AO SEVASTOPOL MARINE", "strong")],
        addresses=[{"city": "Sevastopol", "country": "Ukraine"}],
        remarks="SYNTHETIC TEST RECORD - not a real company.",
    ))

    # -- administrative: address corrected on day 2 -----------------------
    nevsky_address = {"address1": "12 Nevsky Prospekt" if day == DAY1 else "12A Nevsky Prospekt",
                      "city": "St. Petersburg", "country": "Russia"}
    entries.append(sdn_entry(
        NEVSKY_UID, last="ZAKRYTOE AKTSIONERNOE OBSHCHESTVO NEVSKY PRIBOR",
        sdn_type="Entity", programs=["RUSSIA-EO14024"],
        addresses=[nevsky_address],
        remarks="SYNTHETIC TEST RECORD - not a real company.",
    ))

    entries.extend(filler_entries())

    publish = "08/03/2026" if day == DAY1 else "08/04/2026"
    body = "\n".join(entries)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<sdnList xmlns="http://tempuri.org/sdnList.xsd">
  <publshInformation>
    <Publish_Date>{publish}</Publish_Date>
    <Record_Count>{len(entries)}</Record_Count>
  </publshInformation>
{body}
</sdnList>
"""


# ---------------------------------------------------------------------------
# BIS, via the trade.gov Consolidated Screening List
# ---------------------------------------------------------------------------

EL_SOURCE = "Entity List (EL) - Bureau of Industry and Security"
MEU_SOURCE = "Military End User (MEU) List - Bureau of Industry and Security"
SDN_SOURCE = "Specially Designated Nationals (SDN) - Treasury Department"


def build_csl(day: str) -> str:
    results = [
        {
            "id": "EL-2024-0311",
            "source": EL_SOURCE,
            "entity_number": 4311,
            "type": "Entity",
            "name": "AKTSIONERNOE OBSHCHESTVO SEVER INSTRUMENT",
            "alt_names": ["AO SEVER INSTRUMENT", "SEVER INSTRUMENT JSC"],
            "addresses": [{"address": "3 Zavodskaya Str.", "city": "Nizhny Novgorod",
                           "state": "", "postal_code": "603000", "country": "RU"}],
            "ids": [{"type": "Tax ID No.", "number": "5260111222", "country": "RU"}],
            "federal_register_notice": "89 FR 41022",
            "start_date": "2024-05-10",
            "license_requirement": "Presumption of denial for all items subject to the EAR.",
            "license_policy": "Presumption of denial",
            "source_list_url": "https://www.bis.doc.gov/entity-list",
            "remarks": "SYNTHETIC TEST RECORD - not a real company.",
        },
        {
            "id": "MEU-2023-0102",
            "source": MEU_SOURCE,
            "entity_number": 102,
            "type": "Entity",
            "name": "OOO URALSKY PRIBOROSTROITELNY ZAVOD",
            "alt_names": ["URAL INSTRUMENT PLANT LLC"],
            "addresses": [{"address": "44 Lenina Ave.", "city": "Yekaterinburg",
                           "state": "", "postal_code": "620014", "country": "RU"}],
            "ids": [],
            "federal_register_notice": "88 FR 12044",
            "start_date": "2023-02-27",
            "license_requirement": "License required for items in Supplement No. 2 to Part 744.",
            "license_policy": "Case-by-case",
            "source_list_url": "https://www.bis.doc.gov/meu-list",
            "remarks": "SYNTHETIC TEST RECORD - not a real company.",
        },
        # Non-BIS entry: must be ignored by the adapter. Diffing OFAC content
        # out of both the SDN XML and the CSL would double-count every OFAC
        # designation.
        {
            "id": "SDN-47120",
            "source": SDN_SOURCE,
            "type": "Entity",
            "name": "PUBLICHNOE AKTSIONERNOE OBSHCHESTVO VOLNA HOLDING",
            "alt_names": ["PAO VOLNA HOLDING"],
            "addresses": [{"address": "", "city": "Moscow", "state": "",
                           "postal_code": "", "country": "RU"}],
            "ids": [],
            "federal_register_notice": "",
            "start_date": "2026-08-04",
            "source_list_url": "https://sanctionssearch.ofac.treas.gov/",
        },
    ]

    if day == DAY2:
        results.append({
            "id": "EL-2026-0918",
            "source": EL_SOURCE,
            "entity_number": 4918,
            "type": "Entity",
            "name": "KASPIY PRECISION MACHINING LLP",
            "alt_names": ["TOO KASPIY PRECISION MACHINING"],
            "addresses": [{"address": "17 Dostyk Ave.", "city": "Almaty",
                           "state": "", "postal_code": "050010", "country": "KZ"}],
            "ids": [{"type": "Registration Number", "number": "180440021234", "country": "KZ"}],
            "federal_register_notice": "91 FR 33218",
            "start_date": "2026-08-04",
            "license_requirement": "Presumption of denial for all items subject to the EAR.",
            "license_policy": "Presumption of denial",
            "source_list_url": "https://www.bis.doc.gov/entity-list",
            "remarks": "SYNTHETIC TEST RECORD - not a real company.",
        })

    return json.dumps(
        {"total": len(results), "date_of_last_update": day, "results": results},
        indent=1,
    )


# ---------------------------------------------------------------------------
# EU Consolidated Financial Sanctions List (FSD 1.1)
# ---------------------------------------------------------------------------

def build_eu(day: str) -> str:
    entities = [
        """  <sanctionEntity logicalId="88301" designationDate="2022-04-08" euReferenceNumber="EU.9911.72">
    <regulation regulationType="amendment" organisationType="council-regulation"
                publicationDate="2022-04-08" numberTitle="2022/580 (OJ L110)" programme="RUS"/>
    <subjectType classificationCode="E"/>
    <nameAlias wholeName="BALTIC MARINE SERVICES OU" regulationLanguage="EN" logicalId="1"/>
    <nameAlias wholeName="BALTIC MARINE SERVICES OSAUHING" regulationLanguage="ET" logicalId="2"/>
    <address street="Sadama tee 4" city="Tallinn" zipCode="10111" countryIso2Code="EE"/>
    <identification identificationTypeDescription="Registration number" number="14477812" countryIso2Code="EE"/>
  </sanctionEntity>""",
    ]

    if day == DAY2:
        entities.append(
            """  <sanctionEntity logicalId="88417" designationDate="2026-08-04" euReferenceNumber="EU.9977.11">
    <regulation regulationType="amendment" organisationType="council-regulation"
                publicationDate="2026-08-04" numberTitle="2026/1431 (OJ L204)" programme="BLR"/>
    <subjectType classificationCode="E"/>
    <nameAlias wholeName="OAO NEMIGA OPTICS" regulationLanguage="EN" logicalId="1"/>
    <nameAlias wholeName="OTKRYTOE AKTSIONERNOE OBSHCHESTVO NEMIGA OPTIKA" regulationLanguage="RU" logicalId="2"/>
    <address street="27 Nemiga Str." city="Minsk" zipCode="220004" countryIso2Code="BY"/>
    <identification identificationTypeDescription="Registration number" number="100233445" countryIso2Code="BY"/>
  </sanctionEntity>"""
        )

    body = "\n".join(entities)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<export xmlns="http://eu.europa.ec/fpi/fsd/export" generationDate="{day}">
{body}
</export>
"""


# ---------------------------------------------------------------------------
# Federal Register
# ---------------------------------------------------------------------------

def build_federal_register(day: str) -> str:
    results = [
        {
            "document_number": "2026-14882",
            "title": ("Implementation of Additional Sanctions Against Russia: Additions to the "
                      "Entity List"),
            "type": "Rule",
            "abstract": ("The Bureau of Industry and Security adds one entity to the Entity List "
                         "under the destination of Kazakhstan for acting contrary to the national "
                         "security or foreign policy interests of the United States."),
            "publication_date": day,
            "effective_on": day,
            "agencies": [{"raw_name": "BUREAU OF INDUSTRY AND SECURITY",
                          "name": "Industry and Security Bureau"}],
            "docket_ids": ["BIS-2026-0031"],
            "cfr_references": [{"title": 15, "part": 744}],
            "html_url": "https://www.federalregister.gov/documents/2026/08/04/2026-14882",
        },
        {
            # The document that makes the watch module earn its place: it does
            # not name a single entity, and it is capable of moving the
            # reimposition date the entire BIS closure depends on.
            "document_number": "2026-14903",
            "title": ("Expansion of End-User Controls for Affiliates of Certain Listed Entities: "
                      "Request for Comment on Scope and Implementation"),
            "type": "Proposed Rule",
            "abstract": ("The Bureau of Industry and Security seeks public comment on the scope "
                         "of the 50 percent affiliates rule scheduled to take effect on "
                         "November 10, 2026, including whether the aggregation standard should "
                         "be modified and whether additional transition relief is warranted."),
            "publication_date": day,
            "effective_on": "",
            "agencies": [{"raw_name": "BUREAU OF INDUSTRY AND SECURITY",
                          "name": "Industry and Security Bureau"}],
            "docket_ids": ["BIS-2025-0044"],
            "cfr_references": [{"title": 15, "part": 744}, {"title": 15, "part": 734}],
            "html_url": "https://www.federalregister.gov/documents/2026/08/04/2026-14903",
        },
        {
            "document_number": "2026-14877",
            "title": "Agency Information Collection Activities; Submission for OMB Review",
            "type": "Notice",
            "abstract": "Routine paperwork submission.",
            "publication_date": day,
            "effective_on": "",
            "agencies": [{"raw_name": "COMMERCE DEPARTMENT", "name": "Commerce Department"}],
            "docket_ids": [],
            "cfr_references": [],
            "html_url": "https://www.federalregister.gov/documents/2026/08/04/2026-14877",
        },
    ]
    return json.dumps({"count": len(results), "results": results}, indent=1)


# ---------------------------------------------------------------------------
# Ownership graph
# ---------------------------------------------------------------------------

SEVER_KEY = stable_key("Entity List (EL)", "AKTSIONERNOE OBSHCHESTVO SEVER INSTRUMENT", "2024-05-10")
KASPIY_KEY = stable_key("Entity List (EL)", "KASPIY PRECISION MACHINING LLP", "2026-08-04")

NODES = f"""entity_id,name,jurisdiction,list_keys
RU-VOLNA-HOLD,PAO Volna Holding,RU,ofac:47120
RU-VOLNA-MASH,OOO Volna Mashinostroenie,RU,
TR-VOLNA-DIS,Volna Dis Ticaret AS,TR,
CY-AEGEAN,Aegean Meridian Holdings Ltd,CY,
AE-MERIDIAN,Meridian General Trading FZE,AE,
KZ-ARAL,Aral Trading LLP,KZ,
RU-SEVER-INST,AO Sever Instrument,RU,{SEVER_KEY}
KZ-KASPIY,Kaspiy Precision Machining LLP,KZ,{KASPIY_KEY}
BY-KARPENKA,Siarhei Karpenka,BY,ofac:31877
BY-NEMIGA,OAO Nemiga Optics,BY,eu:88417
BY-NEMIGA-TRADE,Nemiga Trade House OOO,BY,
EE-BALTIC-MARINE,Baltic Marine Services OU,EE,eu:88301
LV-BALTIC-SUB,Baltic Marine Logistics SIA,LV,
LT-BALTIC-OPS,Baltic Marine Operations UAB,LT,
RU-TITAN-LOG,OOO Titan Logistika,RU,ofac:19004
"""

EDGES = """owner_id,owned_id,percent,band,control_indicators,source,as_of
RU-VOLNA-HOLD,RU-VOLNA-MASH,75,,,RU EGRUL,2025-11-14
RU-VOLNA-MASH,TR-VOLNA-DIS,60,,,TR Ticaret Sicili,2025-06-30
RU-VOLNA-HOLD,CY-AEGEAN,50,,,CY Registrar of Companies,2024-09-02
RU-VOLNA-HOLD,AE-MERIDIAN,30,,,AE free zone filing,2025-03-18
RU-SEVER-INST,AE-MERIDIAN,20,,,AE free zone filing,2025-03-18
RU-VOLNA-MASH,KZ-ARAL,,,,KZ registry - stake not disclosed,2024-12-01
TR-VOLNA-DIS,RU-VOLNA-MASH,5,,,RU EGRUL,2025-11-14
RU-SEVER-INST,KZ-KASPIY,55,,,KZ registry,2025-08-19
BY-KARPENKA,BY-NEMIGA,80,,,BY Unified State Register,2023-04-11
BY-NEMIGA,BY-NEMIGA-TRADE,100,,,BY Unified State Register,2023-04-11
EE-BALTIC-MARINE,LV-BALTIC-SUB,55,,,LV Uznemumu registrs,2025-02-20
EE-BALTIC-MARINE,LT-BALTIC-OPS,30,,right-to-appoint-and-remove-directors,LT Juridiniu asmenu registras,2025-02-20
RU-TITAN-LOG,KZ-ARAL,15,,,KZ registry,2024-12-01
"""


# ---------------------------------------------------------------------------
# Real-source ownership fixtures
#
# In the exact wire formats of the Companies House PSC snapshot (JSON lines)
# and the GLEIF Level 2 relationship file (dotted-header CSV). Every record
# exists to exercise one rule the ingesters claim to apply.
# ---------------------------------------------------------------------------

PSC_RECORDS = [
    # Corporate PSC with a registration number, filed as both shares and votes.
    # The two bands describe ONE holding; summing them would read 100%.
    {"company_number": "SC555001",
     "data": {"kind": "corporate-entity-person-with-significant-control",
              "name": "PAO VOLNA HOLDING",
              "natures_of_control": ["ownership-of-shares-50-to-75-percent",
                                     "voting-rights-50-to-75-percent"],
              "identification": {"registration_number": "1027700070139",
                                 "country_registered": "Russia",
                                 "legal_form": "Public Joint Stock Company"},
              "address": {"country": "Russia", "locality": "Moscow"},
              "notified_on": "2019-03-11", "ceased_on": None}},
    # Ceased holding. Retained in the snapshot; must not become an edge.
    {"company_number": "SC555002",
     "data": {"kind": "corporate-entity-person-with-significant-control",
              "name": "PAO VOLNA HOLDING",
              "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
              "identification": {"registration_number": "1027700070139",
                                 "country_registered": "Russia"},
              "notified_on": "2017-01-04", "ceased_on": "2023-06-30"}},
    # Statement, not a person. Carries no owner.
    {"company_number": "SC555003",
     "data": {"kind": "psc-statement",
              "statement": "no-individual-or-entity-with-signficant-control",
              "notified_on": "2021-08-02"}},
    # Control with no percentage at all: EU test yes, US rules no.
    {"company_number": "SC555004",
     "data": {"kind": "corporate-entity-person-with-significant-control",
              "name": "AEGEAN MERIDIAN HOLDINGS LTD",
              "natures_of_control": ["right-to-appoint-and-remove-directors"],
              "identification": {"registration_number": "HE404912",
                                 "country_registered": "Cyprus"},
              "address": {"country": "Cyprus"},
              "notified_on": "2020-11-19", "ceased_on": None}},
    # Individual PSC: no registration number, redacted date of birth.
    {"company_number": "SC555005",
     "data": {"kind": "individual-person-with-significant-control",
              "name": "Yevgeniy Petrovich Zhuravlyov",
              "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
              "date_of_birth": {"month": 4, "year": 1971},
              "nationality": "Russian",
              "address": {"country": "Russia"},
              "notified_on": "2018-05-30", "ceased_on": None}},
    # Band below the threshold: must not restrict on its own.
    {"company_number": "SC555006",
     "data": {"kind": "corporate-entity-person-with-significant-control",
              "name": "PAO VOLNA HOLDING",
              "natures_of_control": ["ownership-of-shares-25-to-50-percent"],
              "identification": {"registration_number": "1027700070139",
                                 "country_registered": "Russia"},
              "notified_on": "2022-02-01", "ceased_on": None}},
]

GLEIF_RR_HEADER = [
    "Relationship.StartNode.NodeID", "Relationship.StartNode.NodeIDType",
    "Relationship.EndNode.NodeID", "Relationship.EndNode.NodeIDType",
    "Relationship.RelationshipType", "Relationship.RelationshipStatus",
    "Registration.RegistrationStatus",
]

GLEIF_RR_ROWS = [
    # A direct chain: CHILD -> MID -> TOP. Two edges, and the closure derives
    # the rest.
    ["LEICHILD0000000000A1", "LEI", "LEIMID000000000000B2", "LEI",
     "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE", "PUBLISHED"],
    ["LEIMID000000000000B2", "LEI", "LEITOP000000000000C3", "LEI",
     "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE", "PUBLISHED"],
    # The ultimate statement of the same chain. Must NOT become an edge --
    # loading it would count TOP's interest in CHILD twice.
    ["LEICHILD0000000000A1", "LEI", "LEITOP000000000000C3", "LEI",
     "IS_ULTIMATELY_CONSOLIDATED_BY", "ACTIVE", "PUBLISHED"],
    # An ultimate parent with no direct chain to reach it: a hole in the graph,
    # reported rather than hidden.
    ["LEIORPHAN000000000D4", "LEI", "LEITOP000000000000C3", "LEI",
     "IS_ULTIMATELY_CONSOLIDATED_BY", "ACTIVE", "PUBLISHED"],
    # Not live: nobody is attesting to this any more.
    ["LEILAPSED000000000E5", "LEI", "LEITOP000000000000C3", "LEI",
     "IS_DIRECTLY_CONSOLIDATED_BY", "INACTIVE", "PUBLISHED"],
    # A real relationship, but not ownership in the sense the 50% rules use.
    ["LEIBRANCH000000000F6", "LEI", "LEITOP000000000000C3", "LEI",
     "IS_INTERNATIONAL_BRANCH_OF", "ACTIVE", "PUBLISHED"],
]

GLEIF_LEI_HEADER = [
    "LEI", "Entity.LegalName", "Entity.LegalAddress.Country",
    "Entity.LegalJurisdiction", "Entity.EntityStatus",
]

GLEIF_LEI_ROWS = [
    ["LEITOP000000000000C3", "PAO VOLNA HOLDING", "RU", "RU", "ACTIVE"],
    ["LEIMID000000000000B2", "VOLNA DIS TICARET AS", "TR", "TR", "ACTIVE"],
    ["LEICHILD0000000000A1", "MERIDIAN GENERAL TRADING FZE", "AE", "AE", "ACTIVE"],
    ["LEIORPHAN000000000D4", "ARAL TRADING LLP", "KZ", "KZ", "ACTIVE"],
]


def write_ownership_sources() -> None:
    (HERE / "psc").mkdir(exist_ok=True)
    (HERE / "gleif").mkdir(exist_ok=True)

    # JSON lines, not a JSON document -- exactly as Companies House ships it.
    with open(HERE / "psc" / "psc_snapshot_sample.json", "w", encoding="utf-8") as fh:
        for record in PSC_RECORDS:
            fh.write(json.dumps(record) + "\n")

    with open(HERE / "gleif" / "gleif_rr_sample.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(GLEIF_RR_HEADER)
        writer.writerows(GLEIF_RR_ROWS)

    with open(HERE / "gleif" / "gleif_lei_sample.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(GLEIF_LEI_HEADER)
        writer.writerows(GLEIF_LEI_ROWS)


def main() -> None:
    (HERE / "ofac").mkdir(exist_ok=True)
    (HERE / "bis").mkdir(exist_ok=True)
    (HERE / "eu").mkdir(exist_ok=True)
    (HERE / "federal_register").mkdir(exist_ok=True)
    (HERE / "ownership").mkdir(exist_ok=True)

    for day in (DAY1, DAY2):
        (HERE / "ofac" / f"ofac_sdn_{day}.xml").write_text(build_sdn(day), encoding="utf-8")
        (HERE / "bis" / f"bis_csl_{day}.json").write_text(build_csl(day), encoding="utf-8")
        (HERE / "eu" / f"eu_fsd_{day}.xml").write_text(build_eu(day), encoding="utf-8")

    (HERE / "federal_register" / f"federal_register_{DAY2}.json").write_text(
        build_federal_register(DAY2), encoding="utf-8"
    )
    (HERE / "ownership" / "nodes.csv").write_text(NODES, encoding="utf-8")
    (HERE / "ownership" / "edges.csv").write_text(EDGES, encoding="utf-8")
    write_ownership_sources()
    print(f"wrote fixtures for {DAY1} and {DAY2} under {HERE}")


if __name__ == "__main__":
    main()
