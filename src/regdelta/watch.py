"""Rulemaking watch.

Designation feeds answer "who was added to a list". They cannot answer "did the
definition of restricted change", and in export controls that is where the
largest single movements happen.

The Affiliates Rule is the working example and the reason this module exists.
Published 29 September 2025, it extended Entity List and MEU licence
requirements to any entity 50 percent or more owned, in aggregate, by a listed
party. It added no entries to the Entity List. Commerce stated in the preamble
that affiliates would not be listed. A monitor watching list membership scored
that day as quiet while the restricted universe grew by an unknown multiple.

Six weeks later, on 10 November 2025, BIS suspended the rule for one year as
part of the US-China understanding, and wrote the reimposition into the same
final rule: the suspended text is added back to the EAR on 10 November 2026 and
continues indefinitely, unless Commerce acts again. So the rule is currently
not in force, is scheduled to come into force, and the schedule is itself
contingent on a bilateral arrangement that could move.

That is a monitoring problem, not a lookup. `Watchpoint` encodes a scheduled
regulatory change and the docket and CFR parts whose activity would alter it,
and `evaluate_watchpoints` reports both the countdown and any Federal Register
document capable of moving the date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from regdelta.config import AFFILIATES_RULE_REIMPOSITION
from regdelta.schema import RuleDocument

#: Document types that can alter a scheduled effective date. A notice or a
#: correction generally cannot; a rule or proposed rule can.
DATE_MOVING_TYPES: frozenset[str] = frozenset({"Rule", "Proposed Rule"})


@dataclass(frozen=True, slots=True)
class Watchpoint:
    watch_id: str
    title: str
    scheduled_date: str
    cfr_parts: tuple[str, ...]
    docket_ids: tuple[str, ...]
    agencies: tuple[str, ...]
    keywords: tuple[str, ...]
    why_it_matters: str
    #: Which closure regime becomes live or dead when this date passes, so the
    #: countdown can be tied to a number of derived entities rather than left
    #: as a calendar item.
    regime_key: str = ""

    def days_until(self, today: date) -> int:
        target = datetime.strptime(self.scheduled_date, "%Y-%m-%d").date()
        return (target - today).days


WATCHPOINTS: tuple[Watchpoint, ...] = (
    Watchpoint(
        watch_id="bis_affiliates_reimposition",
        title="BIS Affiliates Rule reimposed",
        scheduled_date=AFFILIATES_RULE_REIMPOSITION,
        cfr_parts=("15 CFR 744", "15 CFR 734", "15 CFR 736"),
        docket_ids=("BIS-2025-0044",),
        agencies=("Industry and Security Bureau", "Bureau of Industry and Security"),
        keywords=(
            "affiliates rule",
            "50 percent",
            "fifty percent",
            "entity list",
            "military end user",
            "end-user controls",
        ),
        why_it_matters=(
            "Entity List and MEU licence requirements extend to entities 50% or more owned "
            "in aggregate by listed parties. Affiliates are not themselves listed, so the "
            "Consolidated Screening List stops being a sufficient screening input on this date."
        ),
        regime_key="bis_affiliates",
    ),
)


@dataclass
class WatchFinding:
    watchpoint: Watchpoint
    days_remaining: int
    status: str  # scheduled | imminent | elapsed
    relevant_documents: list[RuleDocument] = field(default_factory=list)

    @property
    def date_may_have_moved(self) -> bool:
        return any(d.doc_type in DATE_MOVING_TYPES for d in self.relevant_documents)

    def to_dict(self) -> dict:
        return {
            "watch_id": self.watchpoint.watch_id,
            "title": self.watchpoint.title,
            "scheduled_date": self.watchpoint.scheduled_date,
            "days_remaining": self.days_remaining,
            "status": self.status,
            "date_may_have_moved": self.date_may_have_moved,
            "why_it_matters": self.watchpoint.why_it_matters,
            "relevant_documents": [d.to_dict() for d in self.relevant_documents],
        }


def document_matches(doc: RuleDocument, watchpoint: Watchpoint) -> bool:
    """Whether a Federal Register document could bear on a watchpoint.

    Deliberately high-recall. Three independent signals -- docket, CFR part,
    keyword-with-agency -- any one of which is enough. A monitoring product
    that misses the rule changing its own effective date has failed at its only
    job; a handful of false positives a week costs an analyst a minute each.
    """
    if set(doc.docket_ids) & set(watchpoint.docket_ids):
        return True
    if set(doc.cfr_parts) & set(watchpoint.cfr_parts):
        return True

    agency_hit = bool(set(doc.agencies) & set(watchpoint.agencies))
    if not agency_hit:
        return False
    haystack = f"{doc.title} {doc.abstract}".casefold()
    return any(keyword in haystack for keyword in watchpoint.keywords)


def evaluate_watchpoints(
    documents: list[RuleDocument],
    today: date,
    imminent_within_days: int = 120,
    watchpoints: tuple[Watchpoint, ...] = WATCHPOINTS,
) -> list[WatchFinding]:
    findings: list[WatchFinding] = []
    for watchpoint in watchpoints:
        days = watchpoint.days_until(today)
        if days < 0:
            status = "elapsed"
        elif days <= imminent_within_days:
            status = "imminent"
        else:
            status = "scheduled"
        findings.append(
            WatchFinding(
                watchpoint=watchpoint,
                days_remaining=days,
                status=status,
                relevant_documents=[d for d in documents if document_matches(d, watchpoint)],
            )
        )
    return sorted(findings, key=lambda f: f.days_remaining)
