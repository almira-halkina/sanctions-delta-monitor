"""Parser tests, run against the committed fixtures in the real wire formats."""

from __future__ import annotations

import json

import pytest

from regdelta.schema import Snapshot
from regdelta.sources import ADAPTERS
from regdelta.sources.base import ParseError
from regdelta.sources.federal_register import FederalRegisterAdapter


@pytest.mark.parametrize("source,suffix,directory", [
    ("ofac_sdn", "xml", "ofac"),
    ("bis_csl", "json", "bis"),
    ("eu_fsd", "xml", "eu"),
])
def test_parses_fixture(fixtures_dir, source, suffix, directory):
    path = fixtures_dir / directory / f"{source}_2026-08-04.{suffix}"
    snapshot = ADAPTERS[source].parse(path.read_bytes(), "2026-08-04")
    assert isinstance(snapshot, Snapshot)
    assert len(snapshot) > 0
    assert all(r.key.startswith(("ofac:", "bis:", "eu:")) for r in snapshot.records.values())


def test_ofac_declared_count_matches_parsed(fixtures_dir):
    """OFAC publishes Record_Count; a mismatch means the parser dropped entries."""
    path = fixtures_dir / "ofac" / "ofac_sdn_2026-08-04.xml"
    snapshot = ADAPTERS["ofac_sdn"].parse(path.read_bytes(), "2026-08-04")
    assert snapshot.declared_count == len(snapshot)


def test_ofac_entity_without_firstname_is_not_typed_as_individual(fixtures_dir):
    path = fixtures_dir / "ofac" / "ofac_sdn_2026-08-04.xml"
    snapshot = ADAPTERS["ofac_sdn"].parse(path.read_bytes(), "2026-08-04")
    volna = snapshot.records["ofac:47120"]
    assert volna.entity_type == "entity"
    assert not volna.name.startswith(" ")


def test_ofac_weak_aliases_are_tagged(fixtures_dir):
    path = fixtures_dir / "ofac" / "ofac_sdn_2026-08-04.xml"
    snapshot = ADAPTERS["ofac_sdn"].parse(path.read_bytes(), "2026-08-04")
    aliases = snapshot.records["ofac:47120"].aliases
    assert any(a.endswith("[weak]") for a in aliases)
    assert any(not a.endswith("[weak]") for a in aliases)


def test_ofac_country_prose_is_normalised_to_iso2(fixtures_dir):
    path = fixtures_dir / "ofac" / "ofac_sdn_2026-08-04.xml"
    snapshot = ADAPTERS["ofac_sdn"].parse(path.read_bytes(), "2026-08-04")
    assert snapshot.records["ofac:47120"].addresses[0].country == "RU"


def test_csl_adapter_ignores_non_bis_lists(fixtures_dir):
    """OFAC content reaches the pipeline through the SDN XML only.

    Taking it from the CSL as well would emit two deltas for one designation.
    """
    path = fixtures_dir / "bis" / "bis_csl_2026-08-04.json"
    snapshot = ADAPTERS["bis_csl"].parse(path.read_bytes(), "2026-08-04")
    assert all(k.startswith("bis:") for k in snapshot.records)
    assert not any("VOLNA" in r.name for r in snapshot.records.values())


def test_eu_first_english_alias_is_the_display_name(fixtures_dir):
    path = fixtures_dir / "eu" / "eu_fsd_2026-08-04.xml"
    snapshot = ADAPTERS["eu_fsd"].parse(path.read_bytes(), "2026-08-04")
    nemiga = snapshot.records["eu:88417"]
    assert nemiga.name == "OAO NEMIGA OPTICS"
    assert "OTKRYTOE AKTSIONERNOE OBSHCHESTVO NEMIGA OPTIKA" in nemiga.aliases


def test_multivalued_fields_are_sorted(fixtures_dir):
    """Order instability between publications must not read as an amendment."""
    path = fixtures_dir / "ofac" / "ofac_sdn_2026-08-04.xml"
    snapshot = ADAPTERS["ofac_sdn"].parse(path.read_bytes(), "2026-08-04")
    for record in snapshot.records.values():
        assert list(record.aliases) == sorted(record.aliases)
        assert list(record.programs) == sorted(record.programs)


@pytest.mark.parametrize("source,payload", [
    ("ofac_sdn", b"<notSdnList/>"),
    ("bis_csl", b"{}"),
    ("eu_fsd", b'<export xmlns="http://eu.europa.ec/fpi/fsd/export"/>'),
])
def test_malformed_payload_raises_rather_than_returning_partial(source, payload):
    """A partial parse produces false delistings for everything it dropped."""
    with pytest.raises(ParseError):
        ADAPTERS[source].parse(payload, "2026-08-04")


def test_federal_register_documents(fixtures_dir):
    path = fixtures_dir / "federal_register" / "federal_register_2026-08-04.json"
    documents = FederalRegisterAdapter().parse_documents(path.read_bytes())
    assert len(documents) == 3
    proposed = [d for d in documents if d.doc_type == "Proposed Rule"]
    assert proposed and "15 CFR 744" in proposed[0].cfr_parts


# -- namespace handling -----------------------------------------------------
#
# Found against the live OFAC endpoint: the served document did not carry the
# namespace the published schema declares, so every namespace-qualified path
# returned nothing and a perfectly good 17,000-entry download parsed to zero
# entries. Zero entries diffed against yesterday is the entire list reported as
# delisted, which is the most dangerous wrong answer this package can produce.

_MINIMAL_SDN = """<sdnList{xmlns}>
  <publshInformation>
    <Publish_Date>08/19/2026</Publish_Date>
    <Record_Count>1</Record_Count>
  </publshInformation>
  <sdnEntry>
    <uid>99001</uid>
    <lastName>TEST ENTITY</lastName>
    <sdnType>Entity</sdnType>
    <programList><program>RUSSIA-EO14024</program></programList>
    <addressList><address><uid>1</uid><city>Moscow</city><country>Russia</country></address></addressList>
  </sdnEntry>
</sdnList>"""


@pytest.mark.parametrize("xmlns", [
    "",                                                  # no namespace at all
    ' xmlns="http://tempuri.org/sdnList.xsd"',           # the documented one
    ' xmlns="https://sanctionslistservice.ofac.treas.gov/sdnList"',  # a different one
])
def test_namespace_is_read_from_the_document(xmlns):
    payload = _MINIMAL_SDN.format(xmlns=xmlns).encode("utf-8")
    snapshot = ADAPTERS["ofac_sdn"].parse(payload, "2026-08-19")
    assert len(snapshot) == 1
    record = snapshot.records["ofac:99001"]
    assert record.name == "TEST ENTITY"
    assert record.entity_type == "entity"
    assert record.addresses[0].country == "RU"
    assert snapshot.declared_count == 1


def test_schema_change_is_reported_as_a_schema_change():
    """Not as an empty list, and not as an outage."""
    payload = b'<sdnList xmlns="http://example.org/new"><distinctParty/></sdnList>'
    with pytest.raises(ParseError) as excinfo:
        ADAPTERS["ofac_sdn"].parse(payload, "2026-08-19")
    message = str(excinfo.value)
    assert "no <sdnEntry> elements" in message
    assert "http://example.org/new" in message      # what the document declares
    assert "distinctParty" in message               # what it contains instead
    assert "schema change, not an empty list" in message


def test_wrong_root_element_names_the_local_tag():
    with pytest.raises(ParseError, match="expected root <sdnList>, got <Sanctions>"):
        ADAPTERS["ofac_sdn"].parse(b'<Sanctions xmlns="http://x"/>', "2026-08-19")


# -- BIS bulk-file shape ----------------------------------------------------
#
# Found in the live bulk download, 2026-08-19: BIS records carry no `type` and
# no `ids` array, and the only per-record identifier is a 56-hex digest that
# trade.gov generates. See the module docstring in sources/bis_csl.py.

def _csl(**overrides):
    base = {
        "id": "b6e959b59898e975daaae8fae3a8da1ec522f9f888cafc0e6401a16d",
        "source": "Entity List (EL) - Bureau of Industry and Security",
        "name": "TEST MACHINE TOOL CO LTD",
        "addresses": [{"address": "1 Test Rd", "city": "Shenzhen", "country": "CN"}],
        "alt_names": None,          # null, not [] -- as the live file has it
        "start_date": "2011-11-21",
        "federal_register_notice": "76 FR 71867",
        "license_requirement": "For all items subject to the EAR.",
        "remarks": "",
    }
    base.update(overrides)
    return json.dumps({"results": [base]}).encode("utf-8")


def test_absent_type_is_reported_as_not_published_not_unknown():
    """'The publisher does not say' and 'we could not tell' are different facts."""
    snap = ADAPTERS["bis_csl"].parse(_csl(), "2026-08-19")
    record = next(iter(snap.records.values()))
    assert record.entity_type == "not-published"


def test_null_alt_names_is_tolerated():
    snap = ADAPTERS["bis_csl"].parse(_csl(alt_names=None), "2026-08-19")
    assert next(iter(snap.records.values())).aliases == ()


def test_key_survives_the_edits_that_happen_most_often():
    """Aliases, licence text and remarks change constantly; the party does not.

    A key that moves when they do turns every amendment into a delisting, which
    is the one delta a customer acts on immediately.
    """
    before = ADAPTERS["bis_csl"].parse(_csl(), "2026-08-19")
    after = ADAPTERS["bis_csl"].parse(
        _csl(
            alt_names=["TEST MACHINE TOOL", "TMT CO"],
            remarks="Updated remarks.",
            license_requirement="Presumption of denial.",
            id="0000000000000000000000000000000000000000000000000000000a",  # digest moved
        ),
        "2026-08-20",
    )
    assert set(before.records) == set(after.records)


def test_key_moves_when_the_party_itself_changes():
    a = ADAPTERS["bis_csl"].parse(_csl(), "2026-08-19")
    b = ADAPTERS["bis_csl"].parse(_csl(name="A DIFFERENT COMPANY LTD"), "2026-08-19")
    c = ADAPTERS["bis_csl"].parse(_csl(start_date="2024-01-01"), "2026-08-19")
    assert set(a.records) != set(b.records)
    assert set(a.records) != set(c.records)


def test_publisher_digest_is_carried_so_its_churn_is_visible():
    """If the digest is content-derived, it shows up as identifier churn."""
    snap = ADAPTERS["bis_csl"].parse(_csl(), "2026-08-19")
    record = next(iter(snap.records.values()))
    assert any(i.id_type == "CSL digest" for i in record.identifiers)


def test_colliding_parties_are_suffixed_not_dropped():
    """Same list, name and date happens -- usually one party at two addresses."""
    payload = json.dumps({"results": [
        json.loads(_csl())["results"][0],
        json.loads(_csl(addresses=[{"city": "Beijing", "country": "CN"}]))["results"][0],
    ]}).encode("utf-8")
    snap = ADAPTERS["bis_csl"].parse(payload, "2026-08-19")
    assert len(snap) == 2
    assert any(k.endswith("#2") for k in snap.records)


def test_bare_list_payload_is_accepted():
    """The bulk download and the search API wrap the same records differently."""
    record = json.loads(_csl())["results"][0]
    snap = ADAPTERS["bis_csl"].parse(json.dumps([record]).encode("utf-8"), "2026-08-19")
    assert len(snap) == 1


def test_ids_are_read_when_the_keyed_api_provides_them():
    snap = ADAPTERS["bis_csl"].parse(
        _csl(ids=[{"type": "Registration Number", "number": "9130", "country": "CN"}]),
        "2026-08-19",
    )
    record = next(iter(snap.records.values()))
    assert any(i.id_type == "Registration Number" for i in record.identifiers)
