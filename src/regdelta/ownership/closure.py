"""Derived restriction: the closure of a designation over an ownership graph.

The published lists name parties. They do not name the entities those parties
control, and under three separate regimes those entities are restricted anyway:

* **OFAC 50 Percent Rule** (guidance of 13 August 2014). Property of entities
  owned 50 percent or more, *in the aggregate, directly or indirectly*, by one
  or more blocked persons is itself blocked, whether or not the entity appears
  on the SDN List.
* **BIS Affiliates Rule** (90 FR 47254, 29 September 2025; suspended
  10 November 2025 to 9 November 2026; reimposed 10 November 2026). Entity List
  and MEU List licence requirements extend to entities 50 percent or more
  owned, individually or in aggregate, by listed parties, in any foreign
  country. Commerce's own preamble states that affiliates will not be added to
  the Entity List, so the Consolidated Screening List will remain a complete
  record of listed parties and an incomplete record of restricted ones.
* **EU ownership or control** (Best Practices 8519/18). Ownership is a holding
  of *more than* 50 percent; control is a separate qualitative test that a
  percentage cannot express and that can be satisfied at any shareholding.

Two things follow, and they are the whole reason this module exists.

**Propagation is a fixed point, not a multiplication.** The intuitive
implementation multiplies percentages along a chain: 60% of 60% is 36%, so the
grandchild is clean. That is not the rule. Once an entity is itself blocked by
operation of the 50 Percent Rule, it *is* a blocked person, and its own
holdings aggregate at face value. 60% of 60% is blocked. The algorithm below
iterates -- mark, re-aggregate, mark again -- until no entity changes status.
Iteration also makes the computation safe on the circular shareholdings that
are common in precisely the structures worth investigating.

**Unknown is not zero.** Registers routinely omit percentages. An entity whose
known blocked-owner aggregate falls below the threshold, but which has blocked
owners holding an unrecorded stake, is neither restricted nor clear. It is
returned as ``INDETERMINATE`` -- a queue for human research, not a verdict.
Collapsing that state into "clear" is how a wholly-owned subsidiary of a
designated parent passes screening.

Regimes are data, not code, so the same graph can be run through all three and
the divergences reported. Those divergences are not academic: an entity held at
exactly 50.0% is restricted under the US rules and unrestricted under the EU
ownership test, and a multinational has to satisfy both.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from regdelta.ownership.graph import OwnershipGraph


class DerivedStatus(str, Enum):
    LISTED = "listed"                  # named on a published list
    RESTRICTED = "restricted"          # not named; restricted by ownership
    INDETERMINATE = "indeterminate"    # blocked owners present, stake unrecorded
    CLEAR = "clear"


@dataclass(frozen=True, slots=True)
class Regime:
    name: str
    citation: str
    threshold: float
    #: ``operator.ge`` for the US rules ("50 percent or more"); ``operator.gt``
    #: for the EU ("more than 50%"). One character of legal text, a materially
    #: different derived set.
    comparator: Callable[[float, float], bool]
    #: Which list sources seed the closure.
    seed_sources: frozenset[str]
    #: Whether non-percentage control indicators alone can restrict an entity.
    control_test: bool = False
    #: Whether stakes held by several restricted owners are summed.
    aggregate: bool = True
    effective_note: str = ""

    def satisfied_by(self, pct: float) -> bool:
        return self.comparator(pct, self.threshold)


REGIMES: dict[str, Regime] = {
    "ofac_50pct": Regime(
        name="OFAC 50 Percent Rule",
        citation="OFAC Revised Guidance on Entities Owned by Blocked Persons, 13 Aug 2014",
        threshold=50.0,
        comparator=operator.ge,
        seed_sources=frozenset({"ofac_sdn"}),
        control_test=False,
        aggregate=True,
        effective_note="In force.",
    ),
    "bis_affiliates": Regime(
        name="BIS Affiliates Rule",
        citation="90 FR 47254 (29 Sep 2025); suspension 90 FR 52099 (12 Nov 2025)",
        threshold=50.0,
        comparator=operator.ge,
        # The Affiliates Rule aggregates across Entity List, MEU List and SDN
        # holdings together, so the seed set is wider than any single list.
        seed_sources=frozenset({"bis_csl", "ofac_sdn"}),
        control_test=False,
        aggregate=True,
        effective_note="Suspended to 9 Nov 2026; reimposed 10 Nov 2026 absent further action.",
    ),
    "eu_ownership_control": Regime(
        name="EU ownership or control",
        citation="Council Best Practices 8519/18, paras 62-63",
        threshold=50.0,
        comparator=operator.gt,  # 'more than 50%'
        seed_sources=frozenset({"eu_fsd"}),
        control_test=True,
        aggregate=True,
        effective_note="In force.",
    ),
}


@dataclass(frozen=True, slots=True)
class Justification:
    """Why an entity holds its derived status."""

    entity_id: str
    status: DerivedStatus
    aggregate_percent: float
    contributing_owners: tuple[tuple[str, float | None], ...]
    unknown_owners: tuple[str, ...]
    control_owners: tuple[str, ...]
    iteration: int  # 0 = seed; 1 = direct; >=2 = indirect

    def explain(self, graph: OwnershipGraph) -> str:
        def label(entity_id: str) -> str:
            node = graph.nodes.get(entity_id)
            return f"{node.name} ({entity_id})" if node and node.name else entity_id

        if self.status is DerivedStatus.LISTED:
            return "named on a published restricted-party list"
        if self.status is DerivedStatus.INDETERMINATE:
            parts = [
                f"{label(o)} holds an unrecorded stake" for o in self.unknown_owners
            ]
            return (
                f"known restricted aggregate {self.aggregate_percent:g}% is below threshold, but "
                + "; ".join(parts)
            )
        if self.control_owners and self.aggregate_percent == 0.0:
            return "control test satisfied by " + ", ".join(label(o) for o in self.control_owners)
        contributions = ", ".join(
            f"{label(o)} {p:g}%" for o, p in self.contributing_owners if p is not None
        )
        hop = "direct" if self.iteration <= 1 else f"indirect, {self.iteration} hops"
        return f"aggregate {self.aggregate_percent:g}% held by restricted owners ({hop}): {contributions}"


@dataclass
class ClosureResult:
    regime: Regime
    status: dict[str, DerivedStatus] = field(default_factory=dict)
    justification: dict[str, Justification] = field(default_factory=dict)
    iterations: int = 0

    def of_status(self, status: DerivedStatus) -> list[str]:
        return sorted(k for k, v in self.status.items() if v is status)

    @property
    def listed(self) -> list[str]:
        return self.of_status(DerivedStatus.LISTED)

    @property
    def derived(self) -> list[str]:
        """Entities restricted by ownership that appear on no published list.

        This is the number the published lists cannot give you.
        """
        return self.of_status(DerivedStatus.RESTRICTED)

    @property
    def indeterminate(self) -> list[str]:
        return self.of_status(DerivedStatus.INDETERMINATE)

    def summary(self) -> dict[str, int]:
        return {
            "listed": len(self.listed),
            "derived_restricted": len(self.derived),
            "indeterminate": len(self.indeterminate),
            "clear": len(self.of_status(DerivedStatus.CLEAR)),
        }


def compute_closure(
    graph: OwnershipGraph,
    listed_keys_by_source: dict[str, set[str]],
    regime: Regime,
    max_iterations: int = 50,
) -> ClosureResult:
    """Propagate restriction through ownership until the set stops growing.

    ``listed_keys_by_source`` maps a source id (``"ofac_sdn"``) to the set of
    record keys currently on that list. A graph node is a seed when any of its
    ``list_keys`` is on a list this regime seeds from -- which is how the same
    graph produces different seed sets for OFAC and for BIS.
    """
    seed_keys: set[str] = set()
    for source in regime.seed_sources:
        seed_keys |= listed_keys_by_source.get(source, set())

    result = ClosureResult(regime=regime)
    restricted: set[str] = set()

    for node in graph:
        if set(node.list_keys) & seed_keys:
            result.status[node.entity_id] = DerivedStatus.LISTED
            result.justification[node.entity_id] = Justification(
                entity_id=node.entity_id,
                status=DerivedStatus.LISTED,
                aggregate_percent=100.0,
                contributing_owners=(),
                unknown_owners=(),
                control_owners=(),
                iteration=0,
            )
            restricted.add(node.entity_id)
        else:
            result.status[node.entity_id] = DerivedStatus.CLEAR

    # Fixed point. Each pass re-evaluates every non-restricted entity against
    # the current restricted set; an entity newly marked in pass N can restrict
    # its own subsidiaries in pass N+1. Terminates because `restricted` only
    # grows and is bounded by the node count -- which is also what makes the
    # computation safe on cyclic shareholdings.
    for iteration in range(1, max_iterations + 1):
        newly_restricted: dict[str, Justification] = {}
        indeterminate: dict[str, Justification] = {}

        for node in graph:
            entity_id = node.entity_id
            if entity_id in restricted:
                continue

            contributions: list[tuple[str, float | None]] = []
            unknown_owners: list[str] = []
            control_owners: list[str] = []
            total = 0.0

            for edge in graph.owners_of(entity_id):
                if edge.owner_id not in restricted:
                    continue
                if regime.control_test and edge.confers_control:
                    control_owners.append(edge.owner_id)
                if edge.percent is None:
                    unknown_owners.append(edge.owner_id)
                    contributions.append((edge.owner_id, None))
                    continue
                contributions.append((edge.owner_id, edge.percent))
                if regime.aggregate:
                    total += edge.percent
                else:
                    total = max(total, edge.percent)

            justification = Justification(
                entity_id=entity_id,
                status=DerivedStatus.RESTRICTED,
                aggregate_percent=round(total, 6),
                contributing_owners=tuple(contributions),
                unknown_owners=tuple(sorted(set(unknown_owners))),
                control_owners=tuple(sorted(set(control_owners))),
                iteration=iteration,
            )

            if regime.satisfied_by(total) or control_owners:
                newly_restricted[entity_id] = justification
            elif unknown_owners:
                indeterminate[entity_id] = Justification(
                    entity_id=entity_id,
                    status=DerivedStatus.INDETERMINATE,
                    aggregate_percent=round(total, 6),
                    contributing_owners=tuple(contributions),
                    unknown_owners=tuple(sorted(set(unknown_owners))),
                    control_owners=tuple(sorted(set(control_owners))),
                    iteration=iteration,
                )

        # Indeterminate is recomputed from scratch each pass and only committed
        # at the end, because an entity that looks indeterminate early can be
        # resolved to restricted once an upstream owner is marked.
        if not newly_restricted:
            result.iterations = iteration - 1
            for entity_id, justification in indeterminate.items():
                if result.status[entity_id] is DerivedStatus.CLEAR:
                    result.status[entity_id] = DerivedStatus.INDETERMINATE
                    result.justification[entity_id] = justification
            return result

        for entity_id, justification in newly_restricted.items():
            restricted.add(entity_id)
            result.status[entity_id] = DerivedStatus.RESTRICTED
            result.justification[entity_id] = justification

    raise RuntimeError(
        f"closure did not converge in {max_iterations} iterations; "
        "this indicates a bug, not a pathological graph -- the restricted set "
        "is monotone and bounded by the node count"
    )


def compare_regimes(
    graph: OwnershipGraph,
    listed_keys_by_source: dict[str, set[str]],
    regime_names: tuple[str, ...] = ("ofac_50pct", "bis_affiliates", "eu_ownership_control"),
) -> dict[str, ClosureResult]:
    return {
        name: compute_closure(graph, listed_keys_by_source, REGIMES[name])
        for name in regime_names
    }


def divergences(results: dict[str, ClosureResult]) -> dict[str, dict[str, str]]:
    """Entities whose derived status is not the same under every regime.

    These are the entities a multinational cannot treat with a single policy:
    restricted for the US arm, clear for the EU arm, or the reverse.
    """
    all_entities: set[str] = set()
    for result in results.values():
        all_entities |= set(result.status)

    out: dict[str, dict[str, str]] = {}
    for entity_id in sorted(all_entities):
        row = {name: result.status[entity_id].value for name, result in results.items()}
        if len(set(row.values())) > 1:
            out[entity_id] = row
    return out
