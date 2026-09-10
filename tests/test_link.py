"""Joining designated parties to graph nodes.

The asymmetry under test throughout: a false negative is a coverage gap the
reconciliation checks already report; a false positive is an assertion that a
named real company is controlled by a sanctioned party.
"""

from __future__ import annotations

from regdelta.ownership.graph import OwnershipGraph, OwnershipNode
from regdelta.ownership.link import Tier, apply_links, link_records
from regdelta.schema import Address, Identifier, Record


def graph_of(*nodes: tuple[str, str, str]) -> OwnershipGraph:
    graph = OwnershipGraph()
    for entity_id, name, jurisdiction in nodes:
        graph.add_node(OwnershipNode(entity_id=entity_id, name=name, jurisdiction=jurisdiction))
    return graph


def record(name: str, *, country: str = "", ids=()) -> Record:
    return Record(
        key="ofac:1",
        source="ofac_sdn",
        name=name,
        addresses=(Address(country=country),) if country else (),
        identifiers=tuple(Identifier(*i) for i in ids),
    )


def test_shared_lei_is_the_strongest_match():
    graph = graph_of(("lei:LEITOP000000000000C3", "SOMETHING ELSE ENTIRELY", "RU"))
    records = {"ofac:1": record("PAO VOLNA HOLDING",
                                ids=[("Legal Entity Number", "LEITOP000000000000C3", "RU")])}
    links = link_records(records, graph).links
    assert links[0].tier is Tier.IDENTIFIER
    assert links[0].seeds_closure
    assert "LEITOP000000000000C3" in links[0].evidence


def test_registration_number_matches_a_companies_house_node():
    graph = graph_of(("gb-coh:SC555001", "", "GB"))
    records = {"ofac:1": record("WHATEVER LTD",
                                ids=[("Registration Number", "SC555001", "GB")])}
    assert link_records(records, graph).links[0].tier is Tier.IDENTIFIER


def test_name_and_country_agreeing_is_enough_to_seed():
    graph = graph_of(("lei:X", "Titan Logistika LLC", "RU"))
    records = {"ofac:1": record("OOO TITAN LOGISTIKA", country="RU")}
    link = link_records(records, graph).links[0]
    assert link.tier is Tier.NAME_AND_COUNTRY
    assert link.seeds_closure


def test_name_matching_but_country_not_is_reviewed_not_seeded():
    """'Alpha Trading Limited' exists in a dozen registers."""
    graph = graph_of(("lei:X", "Titan Logistika LLC", "GB"))
    records = {"ofac:1": record("OOO TITAN LOGISTIKA", country="RU")}
    link = link_records(records, graph).links[0]
    assert link.tier is Tier.NAME_ONLY
    assert not link.seeds_closure


def test_an_ambiguous_name_is_never_seeded():
    graph = graph_of(("lei:X", "Alpha Trading Ltd", "RU"), ("lei:Y", "Alpha Trading LLC", "RU"))
    records = {"ofac:1": record("ALPHA TRADING", country="RU")}
    link = link_records(records, graph).links[0]
    assert link.tier is Tier.NAME_ONLY
    assert "ambiguous" in link.evidence
    assert not link.seeds_closure


def test_transliteration_only_matches_go_to_review():
    """The folding is a recall device with known collisions, not an identification."""
    graph = graph_of(("psc-name:abc", "Evgenii Juravlev", "RU"))
    records = {"ofac:1": record("Yevgeniy Zhuravlyov", country="RU")}
    link = link_records(records, graph).links[0]
    assert link.tier is Tier.TRANSLITERATION
    assert not link.seeds_closure


def test_no_plausible_match_produces_no_link():
    graph = graph_of(("lei:X", "Completely Unrelated Holdings", "DE"))
    records = {"ofac:1": record("PAO VOLNA HOLDING", country="RU")}
    assert link_records(records, graph).links == []


def test_only_seeding_links_reach_the_graph():
    graph = graph_of(
        ("lei:GOOD", "Titan Logistika LLC", "RU"),
        ("lei:WEAK", "Evgenii Juravlev", "RU"),
    )
    records = {
        "ofac:1": record("OOO TITAN LOGISTIKA", country="RU"),
        "ofac:2": Record(key="ofac:2", source="ofac_sdn", name="Yevgeniy Zhuravlyov"),
    }
    links = link_records(records, graph)
    apply_links(graph, links)
    assert graph.nodes["lei:GOOD"].list_keys == ("ofac:1",)
    assert graph.nodes["lei:WEAK"].list_keys == ()
    assert len(links.review) == 1


def test_every_link_carries_its_evidence():
    graph = graph_of(("lei:X", "Titan Logistika LLC", "RU"))
    records = {"ofac:1": record("OOO TITAN LOGISTIKA", country="RU")}
    for link in link_records(records, graph).links:
        assert link.evidence
        assert link.to_dict()["evidence"] == link.evidence
