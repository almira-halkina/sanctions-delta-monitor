"""Federal Register API v1.

Designation feeds answer "who was added". They cannot answer "what changed
about the rules", and in export controls that is where the largest movements
happen. The Affiliates Rule added no entries to the Entity List and expanded
the restricted universe by an unknown multiple; a monitor that watches only
list membership scores that day as quiet.

This adapter pulls documents filtered to the agencies and CFR parts that carry
sanctions and export-control rulemaking, and hands them to `regdelta.watch`,
which decides which ones affect a tracked docket.
"""

from __future__ import annotations

import json
from typing import Any

from regdelta.schema import RuleDocument
from regdelta.sources.base import ParseError, SourceAdapter

#: CFR parts worth watching, and why.
WATCHED_CFR: dict[str, str] = {
    "15 CFR 744": "EAR end-user controls: Entity List, MEU List, Affiliates Rule",
    "15 CFR 734": "EAR scope and de minimis",
    "15 CFR 736": "EAR General Prohibitions",
    "31 CFR 587": "OFAC Russian Harmful Foreign Activities Sanctions Regulations",
    "31 CFR 589": "OFAC Ukraine-Related Sanctions Regulations",
    "31 CFR 548": "OFAC Belarus Sanctions Regulations",
    "31 CFR 560": "OFAC Iranian Transactions and Sanctions Regulations",
}

WATCHED_AGENCIES: frozenset[str] = frozenset({
    "Industry and Security Bureau",
    "Foreign Assets Control Office",
    "Bureau of Industry and Security",
    "Office of Foreign Assets Control",
    "State Department",
})


class FederalRegisterAdapter(SourceAdapter):
    source = "federal_register"
    endpoint = "https://www.federalregister.gov/api/v1/documents.json"

    def parse(self, payload: bytes, as_of: str):  # type: ignore[override]
        raise NotImplementedError("Federal Register yields RuleDocuments, not a Snapshot")

    def parse_documents(self, payload: bytes) -> list[RuleDocument]:
        try:
            doc = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Federal Register payload is not valid JSON: {exc}") from exc

        results = doc.get("results")
        if not isinstance(results, list):
            raise ParseError("Federal Register payload has no 'results' array")

        return [self._document(item) for item in results]

    @staticmethod
    def _document(item: dict[str, Any]) -> RuleDocument:
        agencies = tuple(sorted({
            (a.get("name") or a.get("raw_name") or "").strip()
            for a in item.get("agencies") or []
        } - {""}))

        cfr_parts = tuple(sorted({
            f"{r.get('title')} CFR {r.get('part')}"
            for r in item.get("cfr_references") or []
            if r.get("title") and r.get("part")
        }))

        return RuleDocument(
            document_number=(item.get("document_number") or "").strip(),
            title=(item.get("title") or "").strip(),
            doc_type=(item.get("type") or "").strip(),
            publication_date=(item.get("publication_date") or "").strip(),
            effective_on=(item.get("effective_on") or "") or "",
            agencies=agencies,
            cfr_parts=cfr_parts,
            docket_ids=tuple(sorted(item.get("docket_ids") or [])),
            abstract=(item.get("abstract") or "").strip(),
            html_url=(item.get("html_url") or "").strip(),
        )
