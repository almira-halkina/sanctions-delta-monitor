"""Ingesting real public ownership data.

Exercised against fixtures in the exact wire formats: Companies House PSC
JSON-lines, and GLEIF Level 2 dotted-header CSV.
"""

from __future__ import annotations

import pytest

from regdelta.ownership.sources import CompaniesHousePsc, GleifLevel2
from regdelta.ownership.sources.companies_house import _percent_and_control, psc_node_id
from regdelta.ownership.sources.gleif import column_index


@pytest.fixture(scope="module")
def psc(fixtures_dir):
    return CompaniesHousePsc().ingest(fixtures_dir / "psc" / "psc_snapshot_sample.json")


@pytest.fixture(scope="module")
def gleif(fixtures_dir):
    return GleifLevel2().ingest(
        fixtures_dir / "gleif" / "gleif_rr_sample.csv",
        lei_path=fixtures_dir / "gleif" / "gleif_lei_sample.csv",
    )


# -- Companies House --------------------------------------------------------

def test_shares_and_votes_for_one_holding_are_not_summed():
    """A single 50-75% holding is filed twice. Summing reads it as 100-150%."""
    percent, _ = _percent_and_control(
        ["ownership-of-shares-50-to-75-percent", "voting-rights-50-to-75-percent"]
    )
    assert percent == 50.0


def test_bands_are_read_at_their_floor():
    percent, _ = _percent_and_control(["ownership-of-shares-25-to-50-percent"])
    assert percent == 25.0  # cannot trip a 50% threshold on its own


def test_control_without_a_percentage_is_kept_as_a_control_indicator():
    percent, controls = _percent_and_control(["right-to-appoint-and-remove-directors"])
    assert percent is None
    assert controls == ("right-to-appoint-and-remove-directors",)


def test_ceased_holdings_do_not_become_edges(psc):
    """Deriving a restriction from a shareholding disposed of years ago."""
    assert psc.skipped.get("ceased holding") == 1
    assert not any(e.owned_id == "gb-coh:SC555002" for e in psc.edges)


def test_statements_are_not_owners(psc):
    assert any(reason.startswith("not a psc record") for reason in psc.skipped)
    assert not any(e.owned_id == "gb-coh:SC555003" for e in psc.edges)


def test_corporate_psc_is_keyed_on_its_registration_number(psc):
    edge = next(e for e in psc.edges if e.owned_id == "gb-coh:SC555001")
    assert edge.owner_id == "psc-reg:RU:1027700070139"
    assert edge.percent == 50.0


def test_individual_psc_is_keyed_on_name_and_redacted_birth_date():
    """The register withholds the day, so that is the most identity available."""
    same = {"name": "Yevgeniy Petrovich Zhuravlyov", "date_of_birth": {"month": 4, "year": 1971}}
    other_month = {"name": "Yevgeniy Petrovich Zhuravlyov", "date_of_birth": {"month": 5, "year": 1971}}
    assert psc_node_id(same) == psc_node_id(dict(same))
    assert psc_node_id(same) != psc_node_id(other_month)
    assert psc_node_id(same).startswith("psc-name:")


def test_every_live_holding_produced_an_edge(psc):
    owned = {e.owned_id for e in psc.edges}
    assert owned == {
        "gb-coh:SC555001",  # 50-75% shares and votes
        "gb-coh:SC555004",  # control only, no percentage
        "gb-coh:SC555005",  # individual, 75-100%
        "gb-coh:SC555006",  # 25-50%, below threshold but still an edge
    }


# -- GLEIF ------------------------------------------------------------------

def test_columns_are_matched_on_their_trailing_segment():
    """GLEIF has renamed prefixes between format versions."""
    header = ["Relationship.StartNode.NodeID", "Relationship.EndNode.NodeID"]
    assert column_index(header, "startnode.nodeid") == 0
    assert column_index(header, "endnode.nodeid") == 1
    assert column_index(header, "nothing.here") is None


def test_a_format_change_fails_loudly_rather_than_returning_zero_rows(tmp_path):
    path = tmp_path / "renamed.csv"
    path.write_text("SomeOther.Column,AndAnother\nx,y\n", encoding="utf-8")
    with pytest.raises(ValueError, match="format change, not an empty file"):
        GleifLevel2().ingest(path)


def test_only_direct_consolidation_becomes_an_edge(gleif):
    """Loading ultimate too would count the same interest twice."""
    pairs = {(e.owner_id, e.owned_id) for e in gleif.edges}
    assert pairs == {
        ("lei:LEIMID000000000000B2", "lei:LEICHILD0000000000A1"),
        ("lei:LEITOP000000000000C3", "lei:LEIMID000000000000B2"),
    }
    assert ("lei:LEITOP000000000000C3", "lei:LEICHILD0000000000A1") not in pairs


def test_gleif_edges_carry_no_percentage_and_never_invent_one(gleif):
    assert all(e.percent is None for e in gleif.edges)
    assert all("accounting-consolidation" in e.control_indicators for e in gleif.edges)


def test_inactive_and_non_ownership_relationships_are_skipped(gleif):
    assert gleif.skipped.get("relationship not active") == 1
    assert gleif.skipped.get("relationship type IS_INTERNATIONAL_BRANCH_OF") == 1


def test_unreachable_ultimate_parents_are_reported(gleif):
    """An ultimate parent the direct chain cannot reach is a hole, not a fact."""
    source = GleifLevel2()
    source.ingest.__self__  # noqa: B018 - documents that state lives on the instance
    assert any("not reachable" in reason for reason in gleif.skipped)


def test_names_come_from_the_level_one_file(gleif):
    names = {n.entity_id: n.name for n in gleif.nodes}
    assert names["lei:LEITOP000000000000C3"] == "PAO VOLNA HOLDING"
    assert {n.jurisdiction for n in gleif.nodes} >= {"RU", "TR", "AE"}
