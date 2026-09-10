"""The analyst brief.

The output of this pipeline is not a dataset, it is a decision. An analyst
arriving on Monday has to know, in under five minutes: what moved, which of it
changes screening behaviour, how many entities became restricted without being
named anywhere, and whether any of the reconciliation checks say the answer
cannot be trusted.

So the brief is ordered by consequence, not by source or by time. Derived
restrictions come first, because they are the finding no published list
contains. Reconciliation failures come before findings, because a failed check
means the findings below it are unsafe -- an analyst who reads the numbers
first and the caveat second has already acted on the numbers.

Numbers that could not be computed are printed as gaps rather than zeros. A
zero in an analyst-facing product is a claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from regdelta.classify import ClassifiedDelta, EventType
from regdelta.normalize import country_name
from regdelta.ownership.closure import ClosureResult, DerivedStatus
from regdelta.ownership.graph import OwnershipGraph
from regdelta.qa import QAReport
from regdelta.watch import WatchFinding


@dataclass
class Brief:
    as_of: str
    deltas: list[ClassifiedDelta] = field(default_factory=list)
    closures: dict[str, ClosureResult] = field(default_factory=dict)
    new_derived: dict[str, list[str]] = field(default_factory=dict)
    released_derived: dict[str, list[str]] = field(default_factory=dict)
    divergent: dict[str, dict[str, str]] = field(default_factory=dict)
    watch: list[WatchFinding] = field(default_factory=list)
    qa: QAReport | None = None
    graph: OwnershipGraph | None = None
    source_notes: list[str] = field(default_factory=list)

    # -- helpers ----------------------------------------------------------

    def _label(self, entity_id: str) -> str:
        if self.graph and entity_id in self.graph.nodes:
            node = self.graph.nodes[entity_id]
            jurisdiction = f", {country_name(node.jurisdiction)}" if node.jurisdiction else ""
            return f"{node.name or entity_id}{jurisdiction}"
        return entity_id

    def _by_event(self, event_type: EventType) -> list[ClassifiedDelta]:
        return [d for d in self.deltas if d.event_type is event_type]

    # -- rendering --------------------------------------------------------

    def to_markdown(self) -> str:
        lines: list[str] = []
        w = lines.append

        w(f"# Restricted-party change brief — {self.as_of}")
        w("")

        # 1. Reconciliation first: it governs whether anything below is usable.
        if self.qa is not None:
            if self.qa.failed:
                w("## Reconciliation FAILED — findings below are not safe to act on")
                w("")
                for check in self.qa.failed:
                    w(f"- **{check.name}** — {check.message}")
                w("")
            elif self.qa.warnings:
                w("## Reconciliation passed with warnings")
                w("")
                for check in self.qa.warnings:
                    w(f"- **{check.name}** — {check.message}")
                w("")

        # 2. Headline.
        w("## Headline")
        w("")
        counts = {e: len(self._by_event(e)) for e in EventType}
        w(f"- {_plural(counts[EventType.NEW_DESIGNATION], 'new designation')}, "
          f"{_plural(counts[EventType.DELISTING], 'delisting')}, "
          f"{_plural(counts[EventType.RE_DESIGNATION], 're-designation')}")
        w(f"- {_plural(counts[EventType.ALIAS_EXPANSION], 'alias expansion')} and "
          f"{_plural(counts[EventType.IDENTIFIER_ENRICHMENT], 'identifier enrichment')} — "
          "no change in list membership, but screening recall differs from yesterday")
        screening = sum(1 for d in self.deltas if d.delta.screening_relevant)
        w(f"- {screening} of {len(self.deltas)} changes alter which strings a screening engine matches")
        for regime_key, entity_ids in self.new_derived.items():
            regime_name = self.closures[regime_key].regime.name
            w(f"- **{_plural(len(entity_ids), 'entity', 'entities')} became restricted under "
              f"the {regime_name} without appearing on any published list**")
        for regime_key, entity_ids in self.released_derived.items():
            if entity_ids:
                regime_name = self.closures[regime_key].regime.name
                w(f"- {_plural(len(entity_ids), 'entity', 'entities')} ceased to be restricted "
                  f"under the {regime_name} following an upstream delisting")
        w("")

        # 3. Derived restrictions: the section no published list can produce.
        if self.new_derived:
            w("## Newly restricted by ownership (on no list)")
            w("")
            for regime_key, entity_ids in self.new_derived.items():
                closure = self.closures[regime_key]
                w(f"### {closure.regime.name}")
                w("")
                w(f"*{closure.regime.citation}. {closure.regime.effective_note}*")
                w("")
                if not entity_ids:
                    w("None.")
                    w("")
                    continue
                for entity_id in entity_ids:
                    justification = closure.justification.get(entity_id)
                    why = justification.explain(self.graph) if justification and self.graph else ""
                    w(f"- **{self._label(entity_id)}** — {why}")
                w("")

        if any(self.released_derived.values()):
            w("## No longer restricted by ownership")
            w("")
            for regime_key, entity_ids in self.released_derived.items():
                if not entity_ids:
                    continue
                w(f"### {self.closures[regime_key].regime.name}")
                w("")
                for entity_id in entity_ids:
                    status = self.closures[regime_key].status[entity_id].value
                    w(f"- **{self._label(entity_id)}** — restricted yesterday, now *{status}*; "
                      "the upstream holding that carried the restriction is gone. Continuing to "
                      "block a party that is no longer restricted is its own compliance failure, "
                      "and no published feed says so.")
                w("")

        # 4. Indeterminate: the research queue.
        indeterminate: list[str] = []
        for closure in self.closures.values():
            indeterminate.extend(closure.indeterminate)
        if indeterminate:
            w("## Indeterminate — restricted owner present, stake unrecorded")
            w("")
            w("These cannot be cleared and cannot be restricted from the register alone. "
              "They are a research queue, not a verdict.")
            w("")
            for entity_id in sorted(set(indeterminate)):
                for closure in self.closures.values():
                    justification = closure.justification.get(entity_id)
                    if justification and justification.status is DerivedStatus.INDETERMINATE:
                        why = justification.explain(self.graph) if self.graph else ""
                        w(f"- **{self._label(entity_id)}** — {why}")
                        break
            w("")

        # 5. Regime divergence.
        if self.divergent:
            w("## Regime divergence")
            w("")
            w("Entities whose status is not the same under every regime. A group operating "
              "on both sides of the Atlantic cannot apply one policy to these.")
            w("")
            regimes = sorted({r for row in self.divergent.values() for r in row})
            w("| Entity | " + " | ".join(self.closures[r].regime.name for r in regimes) + " |")
            w("|---|" + "---|" * len(regimes))
            for entity_id, row in self.divergent.items():
                cells = " | ".join(row.get(r, "—") for r in regimes)
                w(f"| {self._label(entity_id)} | {cells} |")
            w("")

        # 6. List changes by consequence.
        w("## List changes")
        w("")
        for event_type in EventType:
            group = self._by_event(event_type)
            if not group:
                continue
            w(f"### {event_type.value.replace('_', ' ').title()} ({len(group)})")
            w("")
            for item in group:
                jurisdictions = ", ".join(country_name(j) for j in item.jurisdictions) or "—"
                flag = " ⚑" if item.high_opacity else ""
                confidence = "" if item.delta.confidence == "high" else " *(needs review)*"
                w(f"- **{item.name}** — {item.delta.source}, {jurisdictions}{flag}{confidence}")
                w(f"  - {item.rationale}")
                for change in item.delta.field_changes:
                    if change.added_values:
                        w(f"  - `{change.field_name}` added: {', '.join(map(str, change.added_values))}")
                    if change.dropped_values:
                        w(f"  - `{change.field_name}` dropped: {', '.join(map(str, change.dropped_values))}")
            w("")

        # 7. Rulemaking watch.
        if self.watch:
            w("## Rulemaking watch")
            w("")
            for finding in self.watch:
                marker = {"imminent": "**IMMINENT**", "elapsed": "**ELAPSED**"}.get(
                    finding.status, "scheduled"
                )
                w(f"### {finding.watchpoint.title} — {marker}, "
                  f"{finding.days_remaining} days ({finding.watchpoint.scheduled_date})")
                w("")
                w(finding.watchpoint.why_it_matters)
                w("")
                if finding.watchpoint.regime_key in self.closures:
                    closure = self.closures[finding.watchpoint.regime_key]
                    w(f"On the current graph this regime would restrict "
                      f"{len(closure.derived)} entities that appear on no published list, "
                      f"with {len(closure.indeterminate)} more indeterminate.")
                    w("")
                if finding.relevant_documents:
                    w("Federal Register activity on the watched dockets and CFR parts:")
                    w("")
                    for doc in finding.relevant_documents:
                        effective = f", effective {doc.effective_on}" if doc.effective_on else ""
                        w(f"- [{doc.doc_type}] {doc.title} ({doc.publication_date}{effective})")
                    if finding.date_may_have_moved:
                        w("")
                        w("A rule or proposed rule touching this docket has published. "
                          "**Confirm the scheduled date before relying on it.**")
                else:
                    w("No Federal Register activity on the watched dockets in this window.")
                w("")

        if self.source_notes:
            w("## Sources")
            w("")
            for note in self.source_notes:
                w(f"- {note}")
            w("")

        return "\n".join(lines)


def to_html(brief: Brief) -> str:
    """Minimal standalone HTML, no dependencies.

    Markdown is converted with a deliberately small subset renderer rather than
    a library, because the brief is emitted into environments where installing
    anything is a procurement conversation.
    """
    body_lines: list[str] = []
    in_list = False
    in_table = False
    for raw in brief.to_markdown().split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("|"):
            if not in_table:
                body_lines.append("<table>")
                in_table = True
            if set(stripped) <= set("|-: "):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            body_lines.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            body_lines.append("</table>")
            in_table = False

        if stripped.startswith("- "):
            indent = len(line) - len(line.lstrip())
            if not in_list:
                body_lines.append("<ul>")
                in_list = True
            body_lines.append(
                f'<li class="{"sub" if indent else "top"}">{_inline(stripped[2:])}</li>'
            )
            continue
        if in_list:
            body_lines.append("</ul>")
            in_list = False

        if stripped.startswith("### "):
            body_lines.append(f"<h3>{_inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            body_lines.append(f"<h2>{_inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            body_lines.append(f"<h1>{_inline(stripped[2:])}</h1>")
        elif stripped:
            body_lines.append(f"<p>{_inline(stripped)}</p>")

    if in_list:
        body_lines.append("</ul>")
    if in_table:
        body_lines.append("</table>")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Restricted-party change brief — {brief.as_of}</title>
<style>
 body {{ font: 15px/1.55 -apple-system, Segoe UI, Roboto, sans-serif; max-width: 46rem;
        margin: 2.5rem auto; padding: 0 1.25rem; color: #16191d; }}
 h1 {{ font-size: 1.5rem; border-bottom: 2px solid #16191d; padding-bottom: .4rem; }}
 h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
 h3 {{ font-size: .95rem; margin-top: 1.4rem; color: #444; }}
 ul {{ padding-left: 1.1rem; }}
 li.sub {{ list-style: none; color: #555; font-size: .9rem; margin-left: .5rem; }}
 code {{ background: #f2f3f5; padding: .1rem .3rem; border-radius: 3px; font-size: .85em; }}
 table {{ border-collapse: collapse; width: 100%; font-size: .9rem; margin: .6rem 0; }}
 td {{ border: 1px solid #dcdfe3; padding: .3rem .5rem; }}
 em {{ color: #666; }}
</style></head><body>
{chr(10).join(body_lines)}
</body></html>"""


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    word = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {word}"


def _inline(text: str) -> str:
    out = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    for marker, tag in (("**", "strong"), ("`", "code"), ("*", "em")):
        parts = out.split(marker)
        if len(parts) > 2:
            rebuilt = parts[0]
            for i, part in enumerate(parts[1:], start=1):
                rebuilt += (f"<{tag}>{part}" if i % 2 else f"</{tag}>{part}")
            out = rebuilt
    return out
