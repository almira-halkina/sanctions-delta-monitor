from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regdelta.ownership.graph import OwnershipEdge, OwnershipGraph, OwnershipNode  # noqa: E402


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return ROOT / "fixtures"


@pytest.fixture
def graph_factory():
    def build(nodes, edges) -> OwnershipGraph:
        graph = OwnershipGraph()
        for entity_id, list_keys in nodes:
            graph.add_node(
                OwnershipNode(entity_id=entity_id, name=entity_id, list_keys=tuple(list_keys))
            )
        for owner, owned, percent, *rest in edges:
            graph.add_edge(
                OwnershipEdge(
                    owner_id=owner,
                    owned_id=owned,
                    percent=percent,
                    control_indicators=tuple(rest[0]) if rest else (),
                )
            )
        return graph

    return build
