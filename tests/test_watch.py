"""The rulemaking watch has to catch a rule that names nobody."""

from __future__ import annotations

from datetime import date

from regdelta.schema import RuleDocument
from regdelta.watch import WATCHPOINTS, document_matches, evaluate_watchpoints

AFFILIATES = WATCHPOINTS[0]


def doc(**kwargs) -> RuleDocument:
    base = {
        "document_number": "2026-1",
        "title": "",
        "doc_type": "Rule",
        "publication_date": "2026-08-04",
    }
    return RuleDocument(**{**base, **kwargs})


def test_matches_on_docket():
    assert document_matches(doc(docket_ids=("BIS-2025-0044",)), AFFILIATES)


def test_matches_on_cfr_part():
    assert document_matches(doc(cfr_parts=("15 CFR 744",)), AFFILIATES)


def test_matches_on_keyword_only_with_the_right_agency():
    keyword_doc = doc(title="Comment on the 50 percent affiliates rule")
    assert not document_matches(keyword_doc, AFFILIATES)
    with_agency = doc(
        title="Comment on the 50 percent affiliates rule",
        agencies=("Industry and Security Bureau",),
    )
    assert document_matches(with_agency, AFFILIATES)


def test_unrelated_notice_does_not_match():
    assert not document_matches(
        doc(doc_type="Notice", title="Agency Information Collection Activities",
            agencies=("Commerce Department",)),
        AFFILIATES,
    )


def test_countdown_and_imminence():
    findings = evaluate_watchpoints([], today=date(2026, 8, 5))
    assert findings[0].days_remaining == 97
    assert findings[0].status == "imminent"

    later = evaluate_watchpoints([], today=date(2026, 11, 11))
    assert later[0].status == "elapsed"

    earlier = evaluate_watchpoints([], today=date(2026, 1, 1))
    assert earlier[0].status == "scheduled"


def test_proposed_rule_flags_the_date_as_possibly_moved():
    """A rule that names no entity can still move the date the closure depends on."""
    findings = evaluate_watchpoints(
        [doc(doc_type="Proposed Rule", docket_ids=("BIS-2025-0044",),
             title="Request for comment on the affiliates rule")],
        today=date(2026, 8, 5),
    )
    assert findings[0].date_may_have_moved

    quiet = evaluate_watchpoints(
        [doc(doc_type="Notice", cfr_parts=("15 CFR 744",), title="Meeting notice")],
        today=date(2026, 8, 5),
    )
    assert not quiet[0].date_may_have_moved
