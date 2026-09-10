"""Validation and reconciliation.

A monitoring pipeline fails quietly. If a parser silently drops half a list,
the diff reports thousands of delistings and every one of them is wrong; if a
fetch returns a stale file, the diff reports nothing and every quiet day is a
lie. Neither failure raises an exception. Both have to be caught by asserting
things that must be true and checking whether they are.

The checks below are ordered by what they protect against:

* **declared vs parsed count** -- catches parser drops. OFAC publishes
  ``Record_Count``; if the parse does not match it, the parse is wrong.
* **stale publication** -- catches a fetch that returned yesterday's bytes.
  A snapshot whose publish date has not advanced is not evidence of a quiet
  day.
* **churn ceiling** -- catches format changes and truncated downloads. A list
  that moves more than a few percent in a day has almost certainly broken,
  not been amended. Threshold is deliberately blunt and deliberately visible.
* **removal plausibility** -- catches identifier renumbering. Delistings are
  rare and individually newsworthy; a source with unstable keys emitting a
  block of them is renumbering, not delisting.
* **orphan list keys** -- catches drift between the lists and the ownership
  graph. A designated party with no node in the graph has no computable tail,
  which is a coverage gap the brief should state rather than hide.
* **unknown-percent share** -- quantifies how much of the graph cannot support
  a threshold test at all, which bounds how much confidence the derived set
  deserves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from regdelta.diff import ChangeType, DiffResult
from regdelta.ownership.graph import OwnershipGraph
from regdelta.schema import Snapshot


class Severity(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    severity: Severity
    message: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "check": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class QAReport:
    checks: list[Check] = field(default_factory=list)

    def add(self, check: Check) -> None:
        self.checks.append(check)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.severity is Severity.FAIL]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.severity is Severity.WARN]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "failed": len(self.failed),
            "warnings": len(self.warnings),
            "checks": [c.to_dict() for c in self.checks],
        }


def check_declared_count(snapshot: Snapshot) -> Check:
    if snapshot.declared_count is None:
        return Check(
            "declared_count",
            Severity.OK,
            f"{snapshot.source}: publisher declares no record count; skipped",
        )
    parsed = len(snapshot)
    if parsed == snapshot.declared_count:
        return Check(
            "declared_count",
            Severity.OK,
            f"{snapshot.source}: parsed {parsed} entries, matching the publisher's declared count",
        )
    return Check(
        "declared_count",
        Severity.FAIL,
        f"{snapshot.source}: parsed {parsed} entries but publisher declares "
        f"{snapshot.declared_count}; the parse is wrong, not the list",
        {"parsed": parsed, "declared": snapshot.declared_count},
    )


def check_publication_advanced(before: Snapshot, after: Snapshot) -> Check:
    if not before.publish_date or not after.publish_date:
        return Check(
            "publication_advanced",
            Severity.OK,
            f"{after.source}: no publication date exposed; skipped",
        )
    if after.publish_date == before.publish_date:
        return Check(
            "publication_advanced",
            Severity.WARN,
            f"{after.source}: publication date unchanged at {after.publish_date}; "
            "this is a re-fetch of the same publication, not a quiet day",
            {"publish_date": after.publish_date},
        )
    return Check(
        "publication_advanced",
        Severity.OK,
        f"{after.source}: publication advanced {before.publish_date} -> {after.publish_date}",
    )


def check_churn_ceiling(
    before: Snapshot,
    after: Snapshot,
    diff: DiffResult,
    ceiling: float = 0.05,
    min_baseline: int = 100,
) -> Check:
    """Proportional churn, but only where a proportion means anything.

    On a list of four entries, one amendment is 25% churn and tells you
    nothing. `min_baseline` is the point below which the ratio is noise, and
    below it the check reports the raw count and declines to judge. Several BIS
    sub-lists and some EU programme lists are genuinely that small; a check
    that fails on them every day is a check an analyst learns to ignore, which
    is worse than not having it.
    """
    baseline = max(len(before), 1)
    churn = len(diff) / baseline
    detail = {"changed": len(diff), "baseline": baseline, "churn": round(churn, 4)}
    if baseline < min_baseline:
        return Check(
            "churn_ceiling",
            Severity.OK,
            f"{after.source}: {len(diff)} of {baseline} entries changed; list is below the "
            f"{min_baseline}-entry floor where a churn ratio is meaningful, so the "
            "proportional test is not applied",
            detail,
        )
    if churn > ceiling:
        return Check(
            "churn_ceiling",
            Severity.FAIL,
            f"{after.source}: {churn:.1%} of entries changed in one publication, above the "
            f"{ceiling:.0%} ceiling; treat as a format change or truncated download until proven otherwise",
            detail,
        )
    return Check(
        "churn_ceiling",
        Severity.OK,
        f"{after.source}: {churn:.2%} of entries changed, within the {ceiling:.0%} ceiling",
        detail,
    )


def check_removal_plausibility(
    diff: DiffResult, key_stability: str, ceiling: int = 25
) -> Check:
    removals = diff.of_type(ChangeType.REMOVED)
    detail = {"removals": len(removals), "key_stability": key_stability}
    if key_stability != "stable" and removals:
        why = {
            "unstable": "the publisher reuses and reassigns identifiers",
            "composed": "keys are composed from name and listing date, so a name correction "
                        "looks like a removal plus an addition",
        }.get(key_stability, f"key stability is '{key_stability}'")
        return Check(
            "removal_plausibility",
            Severity.WARN,
            f"{diff.source}: {len(removals)} apparent removals, and {why}. "
            "Review before reporting these as delistings.",
            detail,
        )
    if len(removals) > ceiling:
        return Check(
            "removal_plausibility",
            Severity.WARN,
            f"{diff.source}: {len(removals)} removals in one publication exceeds the plausibility "
            f"ceiling of {ceiling}; delistings are individually newsworthy and rarely arrive in blocks",
            detail,
        )
    return Check(
        "removal_plausibility",
        Severity.OK,
        f"{diff.source}: {len(removals)} removals, within plausible range",
        detail,
    )


def check_graph_coverage(graph: OwnershipGraph, listed_keys: set[str]) -> Check:
    keys_in_graph: set[str] = set()
    for node in graph:
        keys_in_graph |= set(node.list_keys)
    orphans = sorted(listed_keys - keys_in_graph)
    covered = len(listed_keys) - len(orphans)
    detail = {
        "listed": len(listed_keys),
        "covered": covered,
        "orphans": orphans[:20],
        "orphan_count": len(orphans),
    }
    if not listed_keys:
        return Check("graph_coverage", Severity.OK, "no listed keys to cover", detail)
    ratio = covered / len(listed_keys)
    severity = Severity.WARN if ratio < 0.5 else Severity.OK
    return Check(
        "graph_coverage",
        severity,
        f"{covered}/{len(listed_keys)} listed parties have a node in the ownership graph; "
        f"{len(orphans)} have no computable ownership tail",
        detail,
    )


def check_unknown_percent_share(graph: OwnershipGraph, ceiling: float = 0.4) -> Check:
    edges = [e for edges in graph._incoming.values() for e in edges]
    if not edges:
        return Check("unknown_percent_share", Severity.OK, "graph has no edges", {})
    unknown = sum(1 for e in edges if e.is_unknown_percent)
    share = unknown / len(edges)
    detail = {"edges": len(edges), "unknown": unknown, "share": round(share, 4)}
    severity = Severity.WARN if share > ceiling else Severity.OK
    return Check(
        "unknown_percent_share",
        severity,
        f"{unknown}/{len(edges)} ownership edges ({share:.1%}) carry no percentage and cannot "
        "support a threshold test; derived findings on those paths are indeterminate, not clear",
        detail,
    )


def run_all(
    before: Snapshot,
    after: Snapshot,
    diff: DiffResult,
    key_stability: str,
    graph: OwnershipGraph | None = None,
    listed_keys: set[str] | None = None,
) -> QAReport:
    report = QAReport()
    report.add(check_declared_count(after))
    report.add(check_publication_advanced(before, after))
    report.add(check_churn_ceiling(before, after, diff))
    report.add(check_removal_plausibility(diff, key_stability))
    if graph is not None:
        report.add(check_graph_coverage(graph, listed_keys or set()))
        report.add(check_unknown_percent_share(graph))
    return report


def check_fetch(source: str, error: str | None, origin: str = "") -> Check:
    """Whether the publication was retrieved at all.

    A failed fetch is reported as a failure naming the source rather than
    silently omitted. An outage that produces no output looks identical to a
    day on which nothing happened, and telling those apart is the entire
    purpose of this package.
    """
    if error is None:
        return Check("fetch", Severity.OK, f"{source}: retrieved from {origin}", {"origin": origin})
    return Check(
        "fetch",
        Severity.FAIL,
        f"{source}: could not be retrieved, so this run says nothing about it. {error}",
        {"error": error},
    )


def check_baseline_only(source: str) -> Check:
    """First observation of a source: nothing to compare against yet."""
    return Check(
        "baseline",
        Severity.WARN,
        f"{source}: no earlier snapshot stored, so this run is a baseline. "
        "Change detection begins with the next publication.",
        {},
    )
