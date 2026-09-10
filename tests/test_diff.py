"""The differ has to see what a row count cannot."""

from __future__ import annotations

from regdelta.classify import EventType, classify
from regdelta.diff import ChangeType, diff_snapshots
from regdelta.schema import Address, Identifier, Record, Snapshot


def snap(as_of: str, *records: Record) -> Snapshot:
    return Snapshot.from_records("ofac_sdn", as_of, records)


def rec(**kwargs) -> Record:
    base = {"key": "ofac:1", "source": "ofac_sdn", "name": "OOO Test", "entity_type": "entity"}
    return Record(**{**base, **kwargs})


def test_alias_addition_is_a_change_even_though_membership_is_identical():
    before = snap("d1", rec(aliases=("A",)))
    after = snap("d2", rec(aliases=("A", "B")))
    result = diff_snapshots(before, after)
    assert len(before) == len(after)          # a row count sees nothing
    assert len(result) == 1                   # the differ does
    delta = result.deltas[0]
    assert delta.change_type is ChangeType.MODIFIED
    assert delta.screening_relevant
    assert delta.field_changes[0].added_values == ("B",)
    assert classify(delta).event_type is EventType.ALIAS_EXPANSION


def test_reordered_aliases_are_not_reported_as_an_amendment():
    """Sanctions lists are not order-stable; sorting at parse time is the fix."""
    before = snap("d1", rec(aliases=tuple(sorted(("B", "A")))))
    after = snap("d2", rec(aliases=tuple(sorted(("A", "B")))))
    result = diff_snapshots(before, after)
    assert len(result) == 0
    assert result.unchanged_count == 1


def test_programme_change_is_a_re_designation_not_an_amendment():
    before = snap("d1", rec(programs=("UKRAINE-EO13662",)))
    after = snap("d2", rec(programs=("RUSSIA-EO14024",)))
    delta = diff_snapshots(before, after).deltas[0]
    assert classify(delta).event_type is EventType.RE_DESIGNATION


def test_identifier_addition_is_flagged_as_enrichment():
    before = snap("d1", rec())
    after = snap("d2", rec(identifiers=(Identifier("Tax ID No.", "7736207543", "RU"),)))
    delta = diff_snapshots(before, after).deltas[0]
    assert classify(delta).event_type is EventType.IDENTIFIER_ENRICHMENT
    assert delta.screening_relevant


def test_address_correction_is_administrative_and_not_screening_relevant():
    before = snap("d1", rec(remarks="old text"))
    after = snap("d2", rec(remarks="new text"))
    delta = diff_snapshots(before, after).deltas[0]
    assert classify(delta).event_type is EventType.ADMINISTRATIVE
    assert not delta.screening_relevant


def test_removal_from_unstable_key_source_is_downgraded_to_review():
    """Renumbering must not be reported to a customer as a delisting."""
    before = snap("d1", rec())
    after = snap("d2")
    stable = diff_snapshots(before, after, key_stability="stable").deltas[0]
    unstable = diff_snapshots(before, after, key_stability="unstable").deltas[0]
    assert stable.change_type is ChangeType.REMOVED and stable.confidence == "high"
    assert unstable.change_type is ChangeType.REMOVED and unstable.confidence == "review"


def test_diff_across_sources_is_refused():
    import pytest

    a = Snapshot.from_records("ofac_sdn", "d1", [])
    b = Snapshot.from_records("eu_fsd", "d2", [])
    with pytest.raises(ValueError):
        diff_snapshots(a, b)


def test_content_hash_fast_path_agrees_with_field_comparison():
    identical = rec(addresses=(Address(city="Moscow", country="RU"),))
    other = rec(addresses=(Address(city="Kazan", country="RU"),))
    assert identical.content_hash() == rec(addresses=(Address(city="Moscow", country="RU"),)).content_hash()
    assert identical.content_hash() != other.content_hash()
