"""The closure is where the legal reading is encoded, so it is tested hardest."""

from __future__ import annotations

from regdelta.ownership.closure import (
    REGIMES,
    DerivedStatus,
    compare_regimes,
    compute_closure,
    divergences,
)

SDN = {"ofac_sdn": {"ofac:1"}}


def test_indirect_ownership_is_not_multiplicative(graph_factory):
    """60% of 60% is blocked, not 36%.

    Once an entity is blocked by operation of the 50 Percent Rule it *is* a
    blocked person, and its own holdings count at face value. This is the
    single most common way an implementation gets the rule wrong.
    """
    graph = graph_factory(
        [("X", ["ofac:1"]), ("A", []), ("B", [])],
        [("X", "A", 60.0), ("A", "B", 60.0)],
    )
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.status["A"] is DerivedStatus.RESTRICTED
    assert result.status["B"] is DerivedStatus.RESTRICTED
    assert result.justification["B"].iteration == 2  # reached on the second pass


def test_stakes_of_separate_blocked_owners_aggregate(graph_factory):
    """Two 25% holdings by blocked persons make 50%, and 50% is the threshold."""
    graph = graph_factory(
        [("X", ["ofac:1"]), ("A", []), ("C", [])],
        [("X", "A", 60.0), ("X", "C", 25.0), ("A", "C", 25.0)],
    )
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.status["C"] is DerivedStatus.RESTRICTED
    assert result.justification["C"].aggregate_percent == 50.0


def test_stakes_of_non_blocked_owners_do_not_count(graph_factory):
    graph = graph_factory(
        [("X", ["ofac:1"]), ("A", []), ("C", [])],
        [("X", "A", 40.0), ("A", "C", 100.0), ("X", "C", 20.0)],
    )
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.status["A"] is DerivedStatus.CLEAR
    assert result.status["C"] is DerivedStatus.CLEAR


def test_unknown_percentage_is_indeterminate_not_clear(graph_factory):
    """Treating an unrecorded stake as zero clears wholly-owned subsidiaries."""
    graph = graph_factory([("X", ["ofac:1"]), ("D", [])], [("X", "D", None)])
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.status["D"] is DerivedStatus.INDETERMINATE
    assert result.justification["D"].unknown_owners == ("X",)


def test_unknown_percentage_resolves_when_known_stakes_already_clear_threshold(graph_factory):
    graph = graph_factory(
        [("X", ["ofac:1"]), ("Y", ["ofac:1"]), ("D", [])],
        [("X", "D", 51.0), ("Y", "D", None)],
    )
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.status["D"] is DerivedStatus.RESTRICTED


def test_circular_shareholding_terminates(graph_factory):
    graph = graph_factory(
        [("X", ["ofac:1"]), ("A", []), ("B", [])],
        [("X", "A", 75.0), ("A", "B", 60.0), ("B", "A", 10.0)],
    )
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.status["A"] is DerivedStatus.RESTRICTED
    assert result.status["B"] is DerivedStatus.RESTRICTED
    assert result.iterations < 10


def test_exactly_fifty_percent_splits_us_from_eu(graph_factory):
    """'50 percent or more' versus 'more than 50%'. One word, two answers."""
    graph = graph_factory(
        [("X", ["ofac:1", "eu:1"]), ("E", [])],
        [("X", "E", 50.0)],
    )
    keys = {"ofac_sdn": {"ofac:1"}, "eu_fsd": {"eu:1"}, "bis_csl": set()}
    results = compare_regimes(graph, keys)
    assert results["ofac_50pct"].status["E"] is DerivedStatus.RESTRICTED
    assert results["eu_ownership_control"].status["E"] is DerivedStatus.CLEAR
    assert "E" in divergences(results)


def test_bis_aggregates_entity_list_and_sdn_holdings_together(graph_factory):
    """The Affiliates Rule aggregates across lists; OFAC's rule does not."""
    graph = graph_factory(
        [("SDN", ["ofac:1"]), ("EL", ["bis:2"]), ("JV", [])],
        [("SDN", "JV", 30.0), ("EL", "JV", 20.0)],
    )
    keys = {"ofac_sdn": {"ofac:1"}, "bis_csl": {"bis:2"}, "eu_fsd": set()}
    results = compare_regimes(graph, keys)
    assert results["bis_affiliates"].status["JV"] is DerivedStatus.RESTRICTED
    assert results["ofac_50pct"].status["JV"] is DerivedStatus.CLEAR


def test_eu_control_test_restricts_below_the_ownership_threshold(graph_factory):
    graph = graph_factory(
        [("X", ["eu:1"]), ("T", [])],
        [("X", "T", 30.0, ["right-to-appoint-and-remove-directors"])],
    )
    keys = {"eu_fsd": {"eu:1"}}
    eu = compute_closure(graph, keys, REGIMES["eu_ownership_control"])
    assert eu.status["T"] is DerivedStatus.RESTRICTED
    ofac = compute_closure(graph, {"ofac_sdn": set()}, REGIMES["ofac_50pct"])
    assert ofac.status["T"] is DerivedStatus.CLEAR


def test_delisting_releases_the_downstream_subtree(graph_factory):
    graph = graph_factory(
        [("P", ["ofac:9"]), ("S1", []), ("S2", [])],
        [("P", "S1", 80.0), ("S1", "S2", 100.0)],
    )
    listed = compute_closure(graph, {"ofac_sdn": {"ofac:9"}}, REGIMES["ofac_50pct"])
    delisted = compute_closure(graph, {"ofac_sdn": set()}, REGIMES["ofac_50pct"])
    assert set(listed.derived) == {"S1", "S2"}
    assert delisted.derived == []


def test_listed_entities_are_never_reported_as_derived(graph_factory):
    graph = graph_factory([("X", ["ofac:1"]), ("A", [])], [("X", "A", 90.0)])
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    assert result.listed == ["X"]
    assert result.derived == ["A"]
    assert result.summary()["derived_restricted"] == 1


def test_psc_bands_are_read_conservatively(graph_factory):
    from regdelta.ownership.graph import OwnershipGraph

    graph = OwnershipGraph.from_rows(
        [{"entity_id": "X", "name": "X", "jurisdiction": "GB", "list_keys": "ofac:1"},
         {"entity_id": "A", "name": "A", "jurisdiction": "GB", "list_keys": ""}],
        [{"owner_id": "X", "owned_id": "A", "percent": "",
          "band": "ownership-of-shares-25-to-50-percent"}],
    )
    result = compute_closure(graph, SDN, REGIMES["ofac_50pct"])
    # The band's floor is 25%, which does not reach the threshold on its own.
    # Reading the midpoint would invent a restriction the filing cannot evidence.
    assert result.status["A"] is DerivedStatus.CLEAR
