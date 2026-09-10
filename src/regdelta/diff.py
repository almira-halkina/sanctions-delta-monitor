"""Field-level differ.

The naive approach to sanctions monitoring is to compare yesterday's entry
count to today's. That approach misses the majority of what actually happens on
a list, because most publication days contain no net change in membership at
all -- what changes is the *content* of existing entries.

Three cases the row-count approach reports as a quiet day:

* **Alias addition.** An entry gains a transliteration variant. Membership is
  unchanged; every screening engine in the world now matches a string it did
  not match yesterday. This is a recall change, and it is the single most
  common substantive amendment on the SDN list.
* **Programme change.** An entry moves from one authority to another -- e.g.
  a party designated under a sectoral programme is re-designated as blocked.
  Same name, same key, completely different legal consequence.
* **Identifier addition.** A tax number or registration number is added, which
  is what allows the entry to be joined to a corporate register -- and
  therefore what allows its ownership tail to be computed at all.

So the differ compares the fields, not the rows, and separates "an entry
appeared" from "an entry changed" from "an entry changed in a way that alters
screening behaviour".

One judgement call is encoded here. A key present yesterday and absent today is
reported as `REMOVED`, but only sources whose adapter declares
``key_stability == "stable"`` get that verdict at full confidence. For the EU
and the BIS/MEU feed, where publishers reuse and reassign identifiers, the same
observation is emitted as `REMOVED` with ``confidence="review"``. Reporting a
renumbering as a delisting is the failure mode that erodes trust in a
monitoring product fastest, because a delisting is the one delta a customer
will act on immediately.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from regdelta.schema import (
    DIFFABLE_FIELDS,
    SCREENING_RELEVANT_FIELDS,
    Record,
    Snapshot,
)


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass(frozen=True, slots=True)
class FieldChange:
    field_name: str
    before: Any
    after: Any

    @property
    def added_values(self) -> tuple[Any, ...]:
        if isinstance(self.before, tuple) and isinstance(self.after, tuple):
            return tuple(v for v in self.after if v not in set(self.before))
        return () if self.before == self.after else (self.after,)

    @property
    def dropped_values(self) -> tuple[Any, ...]:
        if isinstance(self.before, tuple) and isinstance(self.after, tuple):
            return tuple(v for v in self.before if v not in set(self.after))
        return () if self.before == self.after else (self.before,)


@dataclass(frozen=True, slots=True)
class Delta:
    key: str
    source: str
    change_type: ChangeType
    name: str
    record: Record | None
    previous: Record | None = None
    field_changes: tuple[FieldChange, ...] = ()
    confidence: str = "high"  # high | review

    @property
    def screening_relevant(self) -> bool:
        """True when this delta changes which strings a screening engine hits."""
        if self.change_type in (ChangeType.ADDED, ChangeType.REMOVED):
            return True
        return any(fc.field_name in SCREENING_RELEVANT_FIELDS for fc in self.field_changes)

    @property
    def changed_fields(self) -> tuple[str, ...]:
        return tuple(fc.field_name for fc in self.field_changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "change_type": self.change_type.value,
            "name": self.name,
            "confidence": self.confidence,
            "screening_relevant": self.screening_relevant,
            "changed_fields": list(self.changed_fields),
            "field_changes": [
                {
                    "field": fc.field_name,
                    "added": list(fc.added_values),
                    "dropped": list(fc.dropped_values),
                }
                for fc in self.field_changes
            ],
        }


@dataclass
class DiffResult:
    source: str
    before_as_of: str
    after_as_of: str
    deltas: list[Delta] = field(default_factory=list)
    unchanged_count: int = 0

    def of_type(self, change_type: ChangeType) -> list[Delta]:
        return [d for d in self.deltas if d.change_type is change_type]

    @property
    def screening_relevant(self) -> list[Delta]:
        return [d for d in self.deltas if d.screening_relevant]

    def __iter__(self) -> Iterator[Delta]:
        return iter(self.deltas)

    def __len__(self) -> int:
        return len(self.deltas)


def diff_snapshots(
    before: Snapshot,
    after: Snapshot,
    key_stability: str = "stable",
) -> DiffResult:
    """Compare two snapshots of the same source field by field."""
    if before.source != after.source:
        raise ValueError(
            f"cannot diff across sources: {before.source} vs {after.source}"
        )

    result = DiffResult(
        source=after.source, before_as_of=before.as_of, after_as_of=after.as_of
    )
    removal_confidence = "high" if key_stability == "stable" else "review"

    before_keys = set(before.records)
    after_keys = set(after.records)

    for key in sorted(after_keys - before_keys):
        rec = after.records[key]
        result.deltas.append(
            Delta(
                key=key,
                source=after.source,
                change_type=ChangeType.ADDED,
                name=rec.name,
                record=rec,
            )
        )

    for key in sorted(before_keys - after_keys):
        rec = before.records[key]
        result.deltas.append(
            Delta(
                key=key,
                source=after.source,
                change_type=ChangeType.REMOVED,
                name=rec.name,
                record=None,
                previous=rec,
                confidence=removal_confidence,
            )
        )

    for key in sorted(before_keys & after_keys):
        old, new = before.records[key], after.records[key]
        # Fast path: a content hash comparison avoids field-by-field work for
        # the ~99.9% of entries that are byte-identical between publications.
        if old.content_hash() == new.content_hash():
            result.unchanged_count += 1
            continue

        old_fields, new_fields = old.diffable(), new.diffable()
        changes = tuple(
            FieldChange(name, old_fields[name], new_fields[name])
            for name in DIFFABLE_FIELDS
            if old_fields[name] != new_fields[name]
        )
        if not changes:  # hash collision or non-diffable churn
            result.unchanged_count += 1
            continue

        result.deltas.append(
            Delta(
                key=key,
                source=after.source,
                change_type=ChangeType.MODIFIED,
                name=new.name,
                record=new,
                previous=old,
                field_changes=changes,
            )
        )

    return result
