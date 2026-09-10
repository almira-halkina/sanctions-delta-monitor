"""Assemble a real ownership graph and join it to the current designations.

    ingest sources -> merge -> link to sanctions -> write nodes.csv + edges.csv

The output is deliberately the same two CSVs the fixture graph uses, so the
closure, the brief and the tests cannot tell a real graph from a synthetic one.
That is the point: if the pipeline needed a different code path for real data,
the synthetic demo would stop being evidence that the real path works.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from regdelta.ownership.graph import OwnershipGraph, OwnershipNode
from regdelta.ownership.link import LinkSet, apply_links, link_records
from regdelta.ownership.sources import CompaniesHousePsc, GleifLevel2, IngestResult
from regdelta.schema import Record


@dataclass
class BuildResult:
    graph: OwnershipGraph
    links: LinkSet
    ingests: dict[str, IngestResult] = field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        lines = [f"graph: {len(self.graph):,} nodes, {self.graph.edge_count:,} edges"]
        for name, ingest in self.ingests.items():
            lines.append(f"  {name}: {ingest.summary()}")
        by_tier = self.links.by_tier()
        lines.append(
            f"links: {len(self.links.seeding):,} seed the closure, "
            f"{len(self.links.review):,} to review"
        )
        for tier, count in sorted(by_tier.items()):
            lines.append(f"  {tier}: {count:,}")
        return lines


def build(
    records: dict[str, Record],
    psc_paths: tuple[Path, ...] = (),
    gleif_rr_paths: tuple[Path, ...] = (),
    gleif_lei_path: Path | None = None,
    limit: int | None = None,
) -> BuildResult:
    graph = OwnershipGraph()
    ingests: dict[str, IngestResult] = {}

    if psc_paths:
        source = CompaniesHousePsc()
        ingest = source.ingest(*psc_paths, limit=limit)
        _merge(graph, ingest)
        ingests[source.name] = ingest

    if gleif_rr_paths:
        source = GleifLevel2()
        ingest = source.ingest(*gleif_rr_paths, limit=limit, lei_path=gleif_lei_path)
        _merge(graph, ingest)
        ingests[source.name] = ingest

    links = link_records(records, graph)
    apply_links(graph, links)
    return BuildResult(graph=graph, links=links, ingests=ingests)


def _merge(graph: OwnershipGraph, ingest: IngestResult) -> None:
    for node in ingest.nodes:
        graph.add_node(node)
    for edge in ingest.edges:
        graph.add_edge(edge)


def write_graph(graph: OwnershipGraph, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = out_dir / "nodes.csv"
    edges_path = out_dir / "edges.csv"

    with open(nodes_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["entity_id", "name", "jurisdiction", "list_keys"])
        for node in sorted(graph, key=lambda n: n.entity_id):
            writer.writerow(
                [node.entity_id, node.name, node.jurisdiction, "|".join(node.list_keys)]
            )

    with open(edges_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["owner_id", "owned_id", "percent", "band", "control_indicators", "source", "as_of"]
        )
        for owned_id in sorted(graph.nodes):
            for edge in graph.owners_of(owned_id):
                writer.writerow(
                    [
                        edge.owner_id,
                        edge.owned_id,
                        "" if edge.percent is None else f"{edge.percent:g}",
                        "",
                        "|".join(edge.control_indicators),
                        edge.source,
                        edge.as_of,
                    ]
                )
    return nodes_path, edges_path


def write_links(links: LinkSet, out_dir: Path) -> tuple[Path, Path]:
    """Two files: what was used, and what a human needs to look at.

    Splitting them is the point. A single file of matches invites reading the
    weak ones as findings; separating them makes the review queue a queue.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    used_path = out_dir / "links.jsonl"
    review_path = out_dir / "links_to_review.csv"

    with open(used_path, "w", encoding="utf-8") as fh:
        for link in links.seeding:
            fh.write(json.dumps(link.to_dict(), sort_keys=True) + "\n")

    with open(review_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["tier", "record_key", "record_name", "entity_id", "evidence"])
        for link in sorted(links.review, key=lambda x: (x.tier.value, x.record_name)):
            writer.writerow(
                [link.tier.value, link.record_key, link.record_name, link.entity_id, link.evidence]
            )
    return used_path, review_path


def graph_with_placeholder_names(graph: OwnershipGraph) -> OwnershipGraph:
    """Give unnamed nodes their id as a label so briefs are readable."""
    for node in list(graph):
        if not node.name:
            graph.add_node(
                OwnershipNode(
                    entity_id=node.entity_id,
                    name=node.entity_id,
                    jurisdiction=node.jurisdiction,
                    list_keys=node.list_keys,
                )
            )
    return graph
