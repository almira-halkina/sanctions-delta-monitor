"""The checks exist to catch the failures that do not raise exceptions."""

from __future__ import annotations

from regdelta.diff import diff_snapshots
from regdelta.qa import (
    Severity,
    check_churn_ceiling,
    check_declared_count,
    check_graph_coverage,
    check_publication_advanced,
    check_removal_plausibility,
    check_unknown_percent_share,
)
from regdelta.schema import Record, Snapshot


def snap(as_of, n, publish_date="", declared=None, start=0):
    records = [
        Record(key=f"ofac:{i}", source="ofac_sdn", name=f"E{i}") for i in range(start, start + n)
    ]
    return Snapshot.from_records("ofac_sdn", as_of, records, publish_date, declared)


def test_parser_drop_is_caught_by_the_declared_count():
    assert check_declared_count(snap("d", 100, declared=100)).severity is Severity.OK
    bad = check_declared_count(snap("d", 90, declared=100))
    assert bad.severity is Severity.FAIL
    assert "the parse is wrong, not the list" in bad.message


def test_stale_refetch_is_not_reported_as_a_quiet_day():
    check = check_publication_advanced(snap("d1", 5, "08/03/2026"), snap("d2", 5, "08/03/2026"))
    assert check.severity is Severity.WARN


def test_churn_ceiling_fires_on_a_large_list():
    before, after = snap("d1", 200), snap("d2", 200, start=100)
    diff = diff_snapshots(before, after)
    assert check_churn_ceiling(before, after, diff).severity is Severity.FAIL


def test_churn_ceiling_declines_to_judge_a_small_list():
    """One amendment on a four-entry list is 25% churn and means nothing."""
    before, after = snap("d1", 4), snap("d2", 3)
    diff = diff_snapshots(before, after)
    check = check_churn_ceiling(before, after, diff)
    assert check.severity is Severity.OK
    assert "floor where a churn ratio is meaningful" in check.message


def test_removals_from_an_unstable_key_source_are_flagged_for_review():
    before, after = snap("d1", 10), snap("d2", 9)
    diff = diff_snapshots(before, after, key_stability="unstable")
    assert check_removal_plausibility(diff, "unstable").severity is Severity.WARN
    diff_stable = diff_snapshots(before, after, key_stability="stable")
    assert check_removal_plausibility(diff_stable, "stable").severity is Severity.OK


def test_graph_coverage_reports_designations_with_no_computable_tail(graph_factory):
    graph = graph_factory([("X", ["ofac:1"])], [])
    check = check_graph_coverage(graph, {"ofac:1", "ofac:2", "ofac:3"})
    assert check.detail["orphan_count"] == 2
    assert check.severity is Severity.WARN


def test_unknown_percent_share_bounds_confidence_in_the_derived_set(graph_factory):
    graph = graph_factory(
        [("X", []), ("A", []), ("B", [])],
        [("X", "A", None), ("X", "B", None)],
    )
    check = check_unknown_percent_share(graph)
    assert check.severity is Severity.WARN
    assert check.detail["share"] == 1.0
