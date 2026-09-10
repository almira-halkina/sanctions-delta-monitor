"""End-to-end run.

    parse -> snapshot -> diff -> classify -> close over ownership -> reconcile -> brief

The stage worth naming is the fifth. The closure is computed twice, once
against the previous publication's listed set and once against the current
one, and the brief reports the *difference between the two derived sets*. That
is what turns a designation into a consequence: not "OFAC added three
entities" but "OFAC added three entities, and eleven more became blocked as a
result, none of which appear on any list".

Running it in both directions also catches the case people forget. A delisting
does not only remove one party; it can release an entire downstream subtree
that was blocked solely through the delisted parent. Continuing to block those
is its own compliance failure, and nothing in the published feed says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from regdelta import snapshot as snapshot_store
from regdelta.classify import classify_all
from regdelta.config import Paths
from regdelta.diff import DiffResult, diff_snapshots
from regdelta.ownership.closure import (
    REGIMES,
    ClosureResult,
    DerivedStatus,
    compute_closure,
    divergences,
)
from regdelta.ownership.graph import OwnershipGraph
from regdelta.qa import (
    QAReport,
    check_baseline_only,
    check_fetch,
    check_graph_coverage,
    check_unknown_percent_share,
    run_all,
)
from regdelta.report import Brief
from regdelta.schema import Snapshot
from regdelta.sources import ADAPTERS
from regdelta.sources.federal_register import FederalRegisterAdapter
from regdelta.watch import evaluate_watchpoints

FIXTURE_SUFFIX: dict[str, str] = {
    "ofac_sdn": "xml",
    "bis_csl": "json",
    "eu_fsd": "xml",
}
FIXTURE_DIR: dict[str, str] = {
    "ofac_sdn": "ofac",
    "bis_csl": "bis",
    "eu_fsd": "eu",
}


@dataclass
class RunResult:
    brief: Brief
    diffs: dict[str, DiffResult]
    qa: QAReport
    closures_before: dict[str, ClosureResult]
    closures_after: dict[str, ClosureResult]


def _fixture_path(fixtures: Path, source: str, as_of: str) -> Path:
    return fixtures / FIXTURE_DIR[source] / f"{source}_{as_of}.{FIXTURE_SUFFIX[source]}"


def load_fixture_snapshot(fixtures: Path, source: str, as_of: str) -> Snapshot:
    path = _fixture_path(fixtures, source, as_of)
    if not path.exists():
        raise FileNotFoundError(f"no fixture for {source} at {as_of}: {path}")
    return ADAPTERS[source].parse(path.read_bytes(), as_of)


def listed_keys_by_source(snapshots: dict[str, Snapshot]) -> dict[str, set[str]]:
    return {source: set(snap.records) for source, snap in snapshots.items()}


def run(
    as_of: str,
    previous: str,
    paths: Paths | None = None,
    today: date | None = None,
) -> RunResult:
    paths = paths or Paths.default()
    paths.ensure()
    today = today or datetime.strptime(as_of, "%Y-%m-%d").date()

    # Fixture and live snapshots live in separate stores. They were shared
    # until a live run diffed the real EU list against a synthetic fixture
    # snapshot left behind by the demo, and reported every real designation as
    # new and every fixture entry as delisted. Two corpora that share a key
    # space but not a universe must never be compared.
    store = paths.snapshots / "fixture"

    # 1-2. Parse both publications and persist them. Persisting before diffing
    # means a bad diff can be re-run without re-fetching from a publisher that
    # has already overwritten the file.
    before: dict[str, Snapshot] = {}
    after: dict[str, Snapshot] = {}
    for source in ADAPTERS:
        before[source] = load_fixture_snapshot(paths.fixtures, source, previous)
        after[source] = load_fixture_snapshot(paths.fixtures, source, as_of)
        snapshot_store.save(before[source], store)
        snapshot_store.save(after[source], store)

    # 3. Diff and classify.
    diffs: dict[str, DiffResult] = {}
    for source, adapter in ADAPTERS.items():
        diffs[source] = diff_snapshots(before[source], after[source], adapter.key_stability)

    all_deltas = [d for result in diffs.values() for d in result.deltas]
    classified = classify_all(all_deltas)

    # 4. Ownership closure, before and after.
    graph = OwnershipGraph.from_csv(
        paths.fixtures / "ownership" / "nodes.csv",
        paths.fixtures / "ownership" / "edges.csv",
    )
    keys_before = listed_keys_by_source(before)
    keys_after = listed_keys_by_source(after)

    closures_before: dict[str, ClosureResult] = {}
    closures_after: dict[str, ClosureResult] = {}
    for regime_key, regime in REGIMES.items():
        closures_before[regime_key] = compute_closure(graph, keys_before, regime)
        closures_after[regime_key] = compute_closure(graph, keys_after, regime)

    new_derived = {
        regime_key: sorted(
            set(closures_after[regime_key].derived) - set(closures_before[regime_key].derived)
        )
        for regime_key in REGIMES
    }
    # "Released" means no longer restricted at all. An entity that was derived
    # yesterday and is named on a list today has not been released -- it has
    # been promoted from derived to listed, and reporting that as a release
    # would tell a customer to unblock a party that is now explicitly
    # designated. The status check is what separates the two.
    released_derived = {
        regime_key: sorted(
            entity_id
            for entity_id in set(closures_before[regime_key].derived)
            - set(closures_after[regime_key].derived)
            if closures_after[regime_key].status[entity_id]
            in (DerivedStatus.CLEAR, DerivedStatus.INDETERMINATE)
        )
        for regime_key in REGIMES
    }

    # 5. Reconciliation.
    qa = QAReport()
    all_listed: set[str] = set()
    for keys in keys_after.values():
        all_listed |= keys
    for source, adapter in ADAPTERS.items():
        source_qa = run_all(
            before[source],
            after[source],
            diffs[source],
            adapter.key_stability,
            graph=graph if source == "ofac_sdn" else None,
            listed_keys=all_listed if source == "ofac_sdn" else None,
        )
        qa.checks.extend(source_qa.checks)

    # 6. Rulemaking watch.
    fr_path = paths.fixtures / "federal_register" / f"federal_register_{as_of}.json"
    documents = (
        FederalRegisterAdapter().parse_documents(fr_path.read_bytes())
        if fr_path.exists()
        else []
    )
    watch = evaluate_watchpoints(documents, today=today)

    brief = Brief(
        as_of=as_of,
        deltas=classified,
        closures=closures_after,
        new_derived={k: v for k, v in new_derived.items() if v},
        released_derived=released_derived,
        divergent=divergences(closures_after),
        watch=watch,
        qa=qa,
        graph=graph,
        source_notes=[
            f"{adapter.source}: {adapter.endpoint} "
            f"(key stability: {adapter.key_stability}), compared {previous} -> {as_of}"
            for adapter in ADAPTERS.values()
        ]
        + [f"federal_register: {FederalRegisterAdapter().endpoint}"],
    )

    return RunResult(
        brief=brief,
        diffs=diffs,
        qa=qa,
        closures_before=closures_before,
        closures_after=closures_after,
    )


# ---------------------------------------------------------------------------
# Live runs
# ---------------------------------------------------------------------------

def _archive_raw(payload: bytes, root: Path, source: str, as_of: str, suffix: str) -> Path:
    """Keep the bytes as published, alongside the parsed snapshot.

    Regulators overwrite in place and publish no history. A parser bug found in
    November has to be re-runnable against August's bytes, and the publisher no
    longer has them.
    """
    path = root / "raw" / source / f"{source}_{as_of}.{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def run_live(
    paths: Paths | None = None,
    today: date | None = None,
    ownership_dir: Path | None = None,
    fr_lookback_days: int = 30,
) -> RunResult:
    """Fetch the current publications and diff against the last stored snapshot.

    Two differences from an offline run, both consequences of live data.

    The comparison date is whatever was last stored, not "yesterday". Fetches
    fail and publication is irregular; a fixed one-day offset silently reports
    every gap as a day with no changes.

    The ownership closure only runs when an ownership graph is supplied whose
    node keys match the live sources. The committed fixture graph is keyed to
    the synthetic corpus and would find no seeds against the real lists, so
    reporting a derived set of zero would be a false negative dressed as a
    finding. Absent a graph, the feed layer runs and the brief says the
    ownership question was not asked.
    """
    from regdelta import fetch as fetch_mod

    paths = paths or Paths.default()
    paths.ensure()
    today = today or date.today()
    as_of = today.isoformat()
    store = paths.snapshots / "live"

    qa = QAReport()
    after: dict[str, Snapshot] = {}
    before: dict[str, Snapshot] = {}
    diffs: dict[str, DiffResult] = {}
    origins: dict[str, str] = {}

    for source, adapter in ADAPTERS.items():
        try:
            result = fetch_mod.fetch_source(source)
        except Exception as exc:
            qa.add(check_fetch(source, str(exc)))
            continue

        # Archive before parsing, not after. A payload that fails to parse is
        # precisely the one worth keeping: it is the evidence needed to work out
        # whether the publisher changed the schema, and the publisher will have
        # overwritten it by the time anyone looks.
        archived = _archive_raw(result.payload, store, source, as_of, FIXTURE_SUFFIX[source])

        try:
            snapshot = adapter.parse(result.payload, as_of)
        except Exception as exc:
            qa.add(
                check_fetch(
                    source,
                    f"retrieved {len(result.payload):,} bytes but did not parse: {exc} "
                    f"Payload kept at {archived}",
                    result.origin,
                )
            )
            continue

        qa.add(check_fetch(source, None, result.origin))
        origins[source] = result.origin
        after[source] = snapshot
        snapshot_store.save(snapshot, store)

        previous_date = snapshot_store.previous_before(store, source, as_of)
        if previous_date is None:
            qa.add(check_baseline_only(source))
            continue

        before[source] = snapshot_store.load(store, source, previous_date)
        diffs[source] = diff_snapshots(before[source], snapshot, adapter.key_stability)
        source_qa = run_all(before[source], snapshot, diffs[source], adapter.key_stability)
        qa.checks.extend(source_qa.checks)

    classified = classify_all([d for result in diffs.values() for d in result.deltas])

    # Rulemaking watch. Independent of the designation feeds and worth running
    # even when every list fetch failed -- a rule that names nobody is exactly
    # the change the feeds cannot show.
    documents = []
    try:
        fr = fetch_mod.fetch_source(
            "federal_register", extra_params=fetch_mod.default_fr_window(today, fr_lookback_days)
        )
        _archive_raw(fr.payload, store, "federal_register", as_of, "json")
        documents = FederalRegisterAdapter().parse_documents(fr.payload)
        qa.add(check_fetch("federal_register", None, fr.origin))
    except Exception as exc:
        qa.add(check_fetch("federal_register", str(exc)))
    watch = evaluate_watchpoints(documents, today=today)

    # Ownership closure, only if a matching graph was supplied.
    graph: OwnershipGraph | None = None
    closures_before: dict[str, ClosureResult] = {}
    closures_after: dict[str, ClosureResult] = {}
    new_derived: dict[str, list[str]] = {}
    released_derived: dict[str, list[str]] = {}
    divergent: dict[str, dict[str, str]] = {}

    if ownership_dir is not None:
        graph = OwnershipGraph.from_csv(ownership_dir / "nodes.csv", ownership_dir / "edges.csv")
        keys_after = listed_keys_by_source(after)
        keys_before = listed_keys_by_source(before) if before else keys_after
        for regime_key, regime in REGIMES.items():
            closures_after[regime_key] = compute_closure(graph, keys_after, regime)
            closures_before[regime_key] = compute_closure(graph, keys_before, regime)
            new_derived[regime_key] = sorted(
                set(closures_after[regime_key].derived) - set(closures_before[regime_key].derived)
            )
            released_derived[regime_key] = sorted(
                entity_id
                for entity_id in set(closures_before[regime_key].derived)
                - set(closures_after[regime_key].derived)
                if closures_after[regime_key].status[entity_id]
                in (DerivedStatus.CLEAR, DerivedStatus.INDETERMINATE)
            )
        divergent = divergences(closures_after)
        all_listed: set[str] = set()
        for keys in keys_after.values():
            all_listed |= keys
        qa.add(check_graph_coverage(graph, all_listed))
        qa.add(check_unknown_percent_share(graph))

    notes = [
        f"{source}: {origin} (key stability: {ADAPTERS[source].key_stability})"
        for source, origin in origins.items()
    ]
    for source in ADAPTERS:
        if source in diffs:
            notes.append(
                f"{source}: compared against stored snapshot "
                f"{diffs[source].before_as_of} -> {as_of}"
            )
    if ownership_dir is None:
        notes.append(
            "ownership closure not run: no ownership graph supplied "
            "(--ownership DIR). The feed layer above is complete; the question "
            "of who else became restricted was not asked."
        )

    brief = Brief(
        as_of=as_of,
        deltas=classified,
        closures=closures_after,
        new_derived={k: v for k, v in new_derived.items() if v},
        released_derived=released_derived,
        divergent=divergent,
        watch=watch,
        qa=qa,
        graph=graph,
        source_notes=notes,
    )

    return RunResult(
        brief=brief,
        diffs=diffs,
        qa=qa,
        closures_before=closures_before,
        closures_after=closures_after,
    )
