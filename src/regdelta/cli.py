"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from regdelta.config import Paths
from regdelta.ownership.closure import REGIMES
from regdelta.pipeline import run, run_live
from regdelta.report import to_html


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def cmd_run(args: argparse.Namespace) -> int:
    paths = Paths.default()
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else date.today()

    if args.live:
        ownership = Path(args.ownership) if args.ownership else None
        print("fetching current publications from OFAC, BIS, the EU and the "
              "Federal Register (this takes a minute; the SDN list is large)...\n")
        result = run_live(paths=paths, today=today, ownership_dir=ownership)
        args.date = today.isoformat()
    else:
        if not args.date or not args.previous:
            print("offline mode needs --date and --previous (or use --live)", file=sys.stderr)
            return 2
        result = run(args.date, args.previous, paths=paths, today=today)

    brief_md = _write(paths.output / f"brief_{args.date}.md", result.brief.to_markdown())
    brief_html = _write(paths.output / f"brief_{args.date}.html", to_html(result.brief))

    deltas_path = paths.output / f"deltas_{args.date}.jsonl"
    with open(deltas_path, "w", encoding="utf-8") as fh:
        for item in result.brief.deltas:
            fh.write(json.dumps(item.to_dict(), sort_keys=True) + "\n")

    derived_path = paths.output / f"derived_restrictions_{args.date}.csv"
    with open(derived_path, "w", encoding="utf-8") as fh:
        fh.write("regime,entity_id,name,jurisdiction,status,aggregate_percent,justification,newly_derived\n")
        for regime_key, closure in result.closures_after.items():
            newly = set(result.brief.new_derived.get(regime_key, []))
            for entity_id in closure.derived + closure.indeterminate:
                node = result.brief.graph.nodes.get(entity_id) if result.brief.graph else None
                justification = closure.justification[entity_id]
                explanation = (
                    justification.explain(result.brief.graph) if result.brief.graph else ""
                ).replace(",", ";")
                fh.write(
                    f"{regime_key},{entity_id},"
                    f"\"{node.name if node else ''}\",{node.jurisdiction if node else ''},"
                    f"{closure.status[entity_id].value},{justification.aggregate_percent},"
                    f"\"{explanation}\",{entity_id in newly}\n"
                )

    _write(paths.output / f"qa_{args.date}.json", json.dumps(result.qa.to_dict(), indent=2))

    print(result.brief.to_markdown())
    print(f"\n---\nwrote {brief_md}\n      {brief_html}\n      {deltas_path}"
          f"\n      {derived_path}\n      {paths.output / f'qa_{args.date}.json'}")

    if not result.qa.ok and args.strict:
        print("\nreconciliation FAILED and --strict is set", file=sys.stderr)
        return 1
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Report what is actually in the snapshot store.

    Exists because "did it really run against the live lists, and did it get
    all of them" is a question the brief does not answer well. The brief
    reports *change*; on a baseline run there is none, so a correct run and a
    silently broken one look similar. This reads the stored snapshots back and
    prints facts that can be checked against the regulators' own pages:
    how many entries, what publication date the file declared, how many bytes
    arrived, and a sample of real names.
    """
    from collections import Counter

    from regdelta import snapshot as snapshot_store
    from regdelta.normalize import country_name
    from regdelta.sources import ADAPTERS

    paths = Paths.default()
    store = paths.snapshots / ("fixture" if args.fixture else "live")
    if not store.is_dir():
        print(f"no snapshot store at {store}. Run `regdelta run --live` first.", file=sys.stderr)
        return 1

    print(f"snapshot store: {store}\n")
    total_entries = 0
    missing: list[str] = []

    for source in ADAPTERS:
        dates = snapshot_store.available(store, source)
        if not dates:
            missing.append(source)
            print(f"{source}\n  NOT PRESENT — this source did not make it into the store\n")
            continue

        as_of = dates[-1]
        snap = snapshot_store.load(store, source, as_of)
        total_entries += len(snap)

        raw = store / "raw" / source / f"{source}_{as_of}.{'json' if source == 'bis_csl' else 'xml'}"
        size = f"{raw.stat().st_size / 1_000_000:.1f} MB" if raw.exists() else "not archived"

        # Declared vs parsed is the check that matters: the publisher states a
        # count in the file, and an independent count of what was parsed either
        # matches it or does not.
        if snap.declared_count is None:
            reconciliation = "publisher declares no count"
        elif snap.declared_count == len(snap):
            reconciliation = f"MATCHES publisher's declared count of {snap.declared_count:,}"
        else:
            reconciliation = (
                f"MISMATCH — publisher declares {snap.declared_count:,}, parsed {len(snap):,}"
            )

        programs = Counter(p for r in snap.records.values() for p in r.programs)
        jurisdictions = Counter(
            a.country for r in snap.records.values() for a in r.addresses if a.country
        )
        types = Counter(r.entity_type for r in snap.records.values())
        # Only identifiers that could actually join to a corporate register
        # count. The CSL digest is a tracking artefact carried for provenance;
        # counting it would report 100% joinability on a source that publishes
        # no registry numbers at all -- a flattering number that is false.
        joinable = sum(
            1
            for r in snap.records.values()
            if any(i.id_type != "CSL digest" for i in r.identifiers)
        )
        provenance_only = sum(
            1
            for r in snap.records.values()
            if r.identifiers and all(i.id_type == "CSL digest" for i in r.identifiers)
        )
        aliases = sum(len(r.aliases) for r in snap.records.values())

        print(f"{source}")
        print(f"  snapshots stored   {len(dates)}  ({', '.join(dates[-3:])})")
        print(f"  latest             {as_of}")
        print(f"  publisher's date   {snap.publish_date or '(none given)'}")
        print(f"  raw payload        {size}")
        print(f"  entries parsed     {len(snap):,}")
        print(f"  reconciliation     {reconciliation}")
        print("  entity types       " + ", ".join(f"{k} {v:,}" for k, v in types.most_common()))
        print(f"  aliases            {aliases:,} across all entries")
        print(f"  registry ids       {joinable:,} ({joinable / max(len(snap), 1):.0%}) "
              f"— tax or registration numbers, joinable to a corporate register")
        if provenance_only:
            print(f"  provenance ids     {provenance_only:,} publisher digests only, "
                  f"not joinable to anything")
        if programs:
            top = ", ".join(f"{k} ({v:,})" for k, v in programs.most_common(args.top))
            print(f"  top programmes     {top}")
        if jurisdictions:
            top = ", ".join(
                f"{country_name(k)} ({v:,})" for k, v in jurisdictions.most_common(args.top)
            )
            print(f"  top jurisdictions  {top}")
        print("  sample entries")
        for record in list(snap.records.values())[: args.sample]:
            programs_str = ", ".join(record.programs[:2]) or "—"
            print(f"    {record.key:<16} {record.name[:58]:<58} {programs_str}")
        print()

    print(f"total entries across all sources: {total_entries:,}")
    if missing:
        print(f"MISSING SOURCES: {', '.join(missing)} — check the fetch checks in the brief")
        return 1
    return 0


def cmd_ownership_build(args: argparse.Namespace) -> int:
    """Assemble a real ownership graph and join it to the current designations."""
    from regdelta import snapshot as snapshot_store
    from regdelta.ownership.build import (
        build,
        graph_with_placeholder_names,
        write_graph,
        write_links,
    )
    from regdelta.sources import ADAPTERS

    paths = Paths.default()
    store = paths.snapshots / "live"
    records = {}
    for source in ADAPTERS:
        dates = snapshot_store.available(store, source)
        if not dates:
            continue
        records.update(snapshot_store.load(store, source, dates[-1]).records)

    if not records:
        print(
            "no live snapshots stored, so there is nothing to link the graph to.\n"
            "Run `regdelta run --live` first.",
            file=sys.stderr,
        )
        return 1

    psc = tuple(Path(p) for p in (args.psc or []))
    rr = tuple(Path(p) for p in (args.gleif_rr or []))
    if not psc and not rr:
        print("give at least one of --psc or --gleif-rr", file=sys.stderr)
        return 2

    print(f"linking against {len(records):,} designated parties from the live store\n")
    result = build(
        records,
        psc_paths=psc,
        gleif_rr_paths=rr,
        gleif_lei_path=Path(args.gleif_lei) if args.gleif_lei else None,
        limit=args.limit,
    )
    graph_with_placeholder_names(result.graph)

    out = Path(args.out)
    nodes_path, edges_path = write_graph(result.graph, out)
    used_path, review_path = write_links(result.links, out)

    for line in result.summary_lines():
        print(line)
    print(f"\nwrote {nodes_path}\n      {edges_path}\n      {used_path}\n      {review_path}")
    print(
        f"\nRun the closure over it with:\n"
        f"  python -m regdelta.cli run --live --ownership {out}"
    )

    if not result.links.seeding:
        print(
            "\nNo designated party matched a node in this graph, so the closure would "
            "report nothing.\nThat is a coverage result, not a clean bill of health -- "
            "see links_to_review.csv.",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_regimes(_: argparse.Namespace) -> int:
    for key, regime in REGIMES.items():
        comparator = ">=" if regime.comparator.__name__ == "ge" else ">"
        print(f"{key}")
        print(f"  {regime.name}")
        print(f"  {regime.citation}")
        print(f"  threshold: {comparator} {regime.threshold:g}%  "
              f"aggregate: {regime.aggregate}  control test: {regime.control_test}")
        print(f"  seeds from: {', '.join(sorted(regime.seed_sources))}")
        print(f"  status: {regime.effective_note}")
        print()
    return 0


def cmd_sources(_: argparse.Namespace) -> int:
    from regdelta.sources import ADAPTERS
    from regdelta.sources.federal_register import WATCHED_CFR, FederalRegisterAdapter

    for adapter in [*ADAPTERS.values(), FederalRegisterAdapter()]:
        print(f"{adapter.source}")
        print(f"  {adapter.endpoint}")
        print(f"  key stability: {getattr(adapter, 'key_stability', 'n/a')}")
        print()
    print("Watched CFR parts:")
    for part, why in WATCHED_CFR.items():
        print(f"  {part} — {why}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="regdelta",
        description="Regulatory change monitoring with ownership propagation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="diff two publications and write the brief")
    run_parser.add_argument("--live", action="store_true",
                            help="fetch the current publications instead of reading fixtures")
    run_parser.add_argument("--date", help="publication to analyse (YYYY-MM-DD); offline mode")
    run_parser.add_argument("--previous", help="publication to compare against; offline mode")
    run_parser.add_argument("--ownership", metavar="DIR",
                            help="directory with nodes.csv and edges.csv; enables the ownership "
                                 "closure on a live run")
    run_parser.add_argument("--today", help="override today's date for the rulemaking countdown")
    run_parser.add_argument("--strict", action="store_true", help="exit non-zero on QA failure")
    run_parser.set_defaults(func=cmd_run)

    ownership = sub.add_parser(
        "ownership", help="build a real ownership graph from public sources"
    )
    ownership_sub = ownership.add_subparsers(dest="ownership_command", required=True)
    build_parser = ownership_sub.add_parser(
        "build", help="ingest PSC and/or GLEIF data and link it to the live designations"
    )
    build_parser.add_argument("--psc", nargs="*", metavar="FILE",
                              help="Companies House PSC snapshot (.zip, .gz or .json lines)")
    build_parser.add_argument("--gleif-rr", nargs="*", metavar="FILE",
                              help="GLEIF Level 2 relationship file (RR-CDF csv)")
    build_parser.add_argument("--gleif-lei", metavar="FILE",
                              help="GLEIF Level 1 file (LEI-CDF csv), for names and countries")
    build_parser.add_argument("--out", default="ownership",
                              help="directory to write nodes.csv and edges.csv into")
    build_parser.add_argument("--limit", type=int,
                              help="stop after N source records; useful for a first look")
    build_parser.set_defaults(func=cmd_ownership_build)

    inspect_parser = sub.add_parser(
        "inspect", help="report what is actually in the snapshot store"
    )
    inspect_parser.add_argument("--fixture", action="store_true",
                                help="inspect the fixture store instead of the live one")
    inspect_parser.add_argument("--sample", type=int, default=3,
                                help="sample entries to print per source")
    inspect_parser.add_argument("--top", type=int, default=8,
                                help="how many programmes and jurisdictions to list")
    inspect_parser.set_defaults(func=cmd_inspect)

    sub.add_parser("regimes", help="print the encoded ownership regimes").set_defaults(
        func=cmd_regimes
    )
    sub.add_parser("sources", help="print the monitored sources").set_defaults(func=cmd_sources)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
