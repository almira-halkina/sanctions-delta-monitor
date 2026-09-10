"""End to end: real-format sources, linked, closed over, written out."""

from __future__ import annotations

from regdelta.ownership.build import build, write_graph, write_links
from regdelta.ownership.closure import REGIMES, DerivedStatus, compute_closure
from regdelta.schema import Address, Identifier, Record


def _records():
    return {
        # Matches the PSC fixture by registration number: the strongest tier.
        "ofac:47120": Record(
            key="ofac:47120",
            source="ofac_sdn",
            name="PUBLICHNOE AKTSIONERNOE OBSHCHESTVO VOLNA HOLDING",
            addresses=(Address(city="Moscow", country="RU"),),
            identifiers=(Identifier("Registration Number", "1027700070139", "RU"),),
        ),
        # Matches the GLEIF fixture by LEI.
        "ofac:99001": Record(
            key="ofac:99001",
            source="ofac_sdn",
            name="VOLNA HOLDING PJSC",
            addresses=(Address(country="RU"),),
            identifiers=(Identifier("Legal Entity Number", "LEITOP000000000000C3", "RU"),),
        ),
    }


def test_build_links_and_closes_over_real_format_sources(fixtures_dir, tmp_path):
    result = build(
        _records(),
        psc_paths=(fixtures_dir / "psc" / "psc_snapshot_sample.json",),
        gleif_rr_paths=(fixtures_dir / "gleif" / "gleif_rr_sample.csv",),
        gleif_lei_path=fixtures_dir / "gleif" / "gleif_lei_sample.csv",
    )

    assert len(result.links.seeding) == 2
    assert {link.tier.value for link in result.links.seeding} == {"identifier"}

    listed = {"ofac_sdn": {"ofac:47120", "ofac:99001"}}

    ofac = compute_closure(result.graph, listed, REGIMES["ofac_50pct"])
    eu = compute_closure(
        result.graph, {"eu_fsd": {"ofac:47120", "ofac:99001"}}, REGIMES["eu_ownership_control"]
    )

    # Companies House gives a band, so the US rule can act on it.
    assert ofac.status["gb-coh:SC555001"] is DerivedStatus.RESTRICTED
    # 25-50% read at its floor cannot reach the threshold.
    assert ofac.status["gb-coh:SC555006"] is DerivedStatus.CLEAR

    # GLEIF gives no percentage, so the same designation is only a question
    # under the US rules...
    assert ofac.status["lei:LEIMID000000000000B2"] is DerivedStatus.INDETERMINATE
    # ...and an answer under the EU control test. This is the divergence that
    # only shows up once real sources are used.
    eu_listed = {"eu_fsd": {"ofac:47120", "ofac:99001"}}
    eu = compute_closure(result.graph, eu_listed, REGIMES["eu_ownership_control"])
    assert eu.status["lei:LEIMID000000000000B2"] is DerivedStatus.RESTRICTED


def test_written_graph_round_trips_through_the_csv_the_closure_reads(fixtures_dir, tmp_path):
    """The real graph must be indistinguishable from the fixture one downstream."""
    from regdelta.ownership.graph import OwnershipGraph

    result = build(
        _records(),
        psc_paths=(fixtures_dir / "psc" / "psc_snapshot_sample.json",),
        gleif_rr_paths=(fixtures_dir / "gleif" / "gleif_rr_sample.csv",),
    )
    nodes_path, edges_path = write_graph(result.graph, tmp_path / "own")
    used, review = write_links(result.links, tmp_path / "own")

    reloaded = OwnershipGraph.from_csv(nodes_path, edges_path)
    assert len(reloaded) == len(result.graph)
    assert reloaded.edge_count == result.graph.edge_count
    assert used.exists() and review.exists()

    # Percentages and control indicators survive the round trip.
    edge = next(e for e in reloaded.owners_of("gb-coh:SC555001"))
    assert edge.percent == 50.0
    consolidated = reloaded.owners_of("lei:LEIMID000000000000B2")[0]
    assert consolidated.percent is None
    assert "accounting-consolidation" in consolidated.control_indicators
