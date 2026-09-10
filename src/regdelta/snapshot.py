"""Dated snapshot store.

Every publication is written to disk before it is diffed, for two reasons that
both come from the same place: regulators overwrite in place. There is no
history endpoint for the SDN list, and once a publication is replaced the
previous state is gone. If the store is the only record of what the list said
yesterday, then a lost snapshot is a permanently unanswerable question about
what changed.

The second reason is replay. A parser bug found in November should be
re-runnable against August's bytes; storing the raw payload alongside the
parsed snapshot makes that a local operation instead of a request to the
publisher for data they no longer have.
"""

from __future__ import annotations

import json
from pathlib import Path

from regdelta.schema import Address, Identifier, Record, Snapshot, SourceId


def _record_to_json(rec: Record) -> dict:
    return {
        "key": rec.key,
        "source": rec.source,
        "name": rec.name,
        "entity_type": rec.entity_type,
        "programs": list(rec.programs),
        "aliases": list(rec.aliases),
        "addresses": [
            {
                "street": a.street,
                "city": a.city,
                "region": a.region,
                "postal_code": a.postal_code,
                "country": a.country,
            }
            for a in rec.addresses
        ],
        "identifiers": [
            {"id_type": i.id_type, "value": i.value, "country": i.country}
            for i in rec.identifiers
        ],
        "nationalities": list(rec.nationalities),
        "remarks": rec.remarks,
        "listing_date": rec.listing_date,
        "license_requirement": rec.license_requirement,
        "source_url": rec.source_url,
    }


def _record_from_json(doc: dict) -> Record:
    return Record(
        key=doc["key"],
        source=doc["source"],
        name=doc["name"],
        entity_type=doc.get("entity_type", "unknown"),
        programs=tuple(doc.get("programs", ())),
        aliases=tuple(doc.get("aliases", ())),
        addresses=tuple(Address(**a) for a in doc.get("addresses", ())),
        identifiers=tuple(Identifier(**i) for i in doc.get("identifiers", ())),
        nationalities=tuple(doc.get("nationalities", ())),
        remarks=doc.get("remarks", ""),
        listing_date=doc.get("listing_date", ""),
        license_requirement=doc.get("license_requirement", ""),
        source_url=doc.get("source_url", ""),
    )


def snapshot_path(root: Path, source: SourceId, as_of: str) -> Path:
    return root / source / f"{as_of}.json"


def save(snapshot: Snapshot, root: Path) -> Path:
    path = snapshot_path(root, snapshot.source, snapshot.as_of)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": snapshot.source,
        "as_of": snapshot.as_of,
        "publish_date": snapshot.publish_date,
        "declared_count": snapshot.declared_count,
        "records": [_record_to_json(r) for r in snapshot.records.values()],
    }
    path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    return path


def load(root: Path, source: SourceId, as_of: str) -> Snapshot:
    path = snapshot_path(root, source, as_of)
    doc = json.loads(path.read_text(encoding="utf-8"))
    return Snapshot.from_records(
        source=doc["source"],
        as_of=doc["as_of"],
        records=[_record_from_json(r) for r in doc["records"]],
        publish_date=doc.get("publish_date", ""),
        declared_count=doc.get("declared_count"),
    )


def available(root: Path, source: SourceId) -> list[str]:
    """Dates for which a parsed snapshot of `source` is stored, oldest first.

    Only files whose stem is a date are counted. The store also holds a `raw/`
    archive of the original payloads, and a stray file there must not be
    mistaken for a publication.
    """
    directory = root / source
    if not directory.is_dir():
        return []
    return sorted(
        p.stem
        for p in directory.glob("*.json")
        if len(p.stem) == 10 and p.stem[4] == "-" and p.stem[7] == "-"
    )


def previous_before(root: Path, source: SourceId, as_of: str) -> str | None:
    """Most recent stored snapshot strictly before `as_of`.

    Diffing against 'the previous stored snapshot' rather than 'yesterday'
    matters because publication is not daily and fetches fail. Comparing
    against a fixed one-day offset silently reports every gap as a day with no
    changes, which is the opposite of the truth.
    """
    earlier = [d for d in available(root, source) if d < as_of]
    return earlier[-1] if earlier else None
