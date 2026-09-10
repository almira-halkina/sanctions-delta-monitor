"""End-to-end, against the committed two-day fixture corpus.

These assertions are the scenario in `docs/findings.md`, pinned so a refactor
that quietly changes the legal reading fails the build.
"""

from __future__ import annotations

from datetime import date

import pytest

from regdelta.config import Paths
from regdelta.pipeline import run
from regdelta.report import to_html


@pytest.fixture(scope="module")
def result(fixtures_dir, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("regdelta")
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp / "snapshots", output=tmp / "output")
    return run("2026-08-04", "2026-08-03", paths=paths, today=date(2026, 8, 5))


def test_all_delta_kinds_are_present(result):
    kinds = {d.event_type.value for d in result.brief.deltas}
    assert kinds == {
        "new_designation",
        "delisting",
        "re_designation",
        "alias_expansion",
        "identifier_enrichment",
        "administrative",
    }


def test_one_designation_produces_three_derived_restrictions_under_ofac(result):
    derived = result.brief.new_derived["ofac_50pct"]
    assert set(derived) == {"RU-VOLNA-MASH", "TR-VOLNA-DIS", "CY-AEGEAN"}


def test_bis_catches_a_joint_venture_that_ofac_does_not(result):
    """30% from an SDN plus 20% from an Entity List party is 50% under BIS only."""
    assert "AE-MERIDIAN" in result.brief.new_derived["bis_affiliates"]
    assert "AE-MERIDIAN" not in result.brief.new_derived["ofac_50pct"]


def test_turkish_subsidiary_is_caught_two_hops_down(result):
    """75% x 60% = 45% under a multiplicative reading; the rule says blocked."""
    justification = result.closures_after["ofac_50pct"].justification["TR-VOLNA-DIS"]
    assert justification.iteration == 2
    assert justification.aggregate_percent == 60.0


def test_delisting_releases_a_subtree_the_feed_says_nothing_about(result):
    released = result.brief.released_derived["ofac_50pct"]
    assert set(released) == {"BY-NEMIGA", "BY-NEMIGA-TRADE"}


def test_promotion_from_derived_to_listed_is_not_reported_as_a_release(result):
    """Kaspiy was derived yesterday and is on the Entity List today."""
    assert "KZ-KASPIY" not in result.brief.released_derived["bis_affiliates"]
    assert result.closures_after["bis_affiliates"].status["KZ-KASPIY"].value == "listed"


def test_undisclosed_stake_lands_in_the_research_queue(result):
    assert "KZ-ARAL" in result.closures_after["ofac_50pct"].indeterminate


def test_regimes_diverge_and_the_brief_says_where(result):
    divergent = result.brief.divergent
    assert divergent["CY-AEGEAN"]["ofac_50pct"] == "restricted"
    assert divergent["CY-AEGEAN"]["eu_ownership_control"] == "clear"


def test_reconciliation_passes(result):
    assert result.qa.ok, [c.message for c in result.qa.failed]


def test_watch_reports_the_countdown_and_the_proposed_rule(result):
    finding = result.brief.watch[0]
    assert finding.watchpoint.watch_id == "bis_affiliates_reimposition"
    assert finding.days_remaining == 97
    assert finding.date_may_have_moved


def test_brief_renders_to_markdown_and_html(result):
    markdown = result.brief.to_markdown()
    assert "Newly restricted by ownership" in markdown
    html = to_html(result.brief)
    assert html.startswith("<!doctype html>")
    assert "<table>" in html
