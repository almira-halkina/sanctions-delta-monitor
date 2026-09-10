"""Retrieval, kept deliberately separate from parsing.

Nothing else in the package imports `requests`, so every parser and every
downstream stage is testable offline against committed fixtures in the real
wire format. That separation is also what makes the fixture corpus honest: the
same code path parses a fixture and a live download.

Three things about fetching government publications shape this module.

**Endpoints move.** OFAC migrated the SDN list from `treasury.gov/ofac/downloads`
to a Sanctions List Service host, and both have been live simultaneously for
some time. Each source therefore declares an ordered list of candidate URLs and
the first one that returns usable bytes wins. A monitor that dies because a
publisher reorganised its file server is a monitor that reports a quiet day.

**Failures are per-source, not fatal.** If the EU webgate is down, the OFAC diff
is still worth having. A failed fetch is recorded, surfaced in the brief as a
reconciliation failure naming the source, and the run continues without it.
Silently dropping the source would turn an outage into a false quiet day, which
is the specific failure this whole package exists to prevent.

**A response with status 200 is not necessarily the file.** Government hosts
return HTML error pages, maintenance notices and login redirects with a 200.
`_looks_like` rejects a payload whose first bytes do not match the format the
adapter expects, so a maintenance page is a fetch failure rather than a parse
failure reported against 19,000 missing entries.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from regdelta.sources.base import SourceAdapter

USER_AGENT = (
    "regdelta/0.1 (open-source sanctions change monitoring; "
    "https://github.com/almira-halkina/sanctions-delta-monitor)"
)
DEFAULT_TIMEOUT = 90
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2.0


class FetchError(RuntimeError):
    """Every candidate endpoint for a source failed."""


@dataclass(frozen=True)
class FetchResult:
    source: str
    payload: bytes
    origin: str  # a URL, or a fixture path


@dataclass(frozen=True)
class Endpoint:
    url: str
    params: dict = field(default_factory=dict)
    #: "xml" or "json" -- what the first non-whitespace bytes must look like.
    expect: str = "xml"
    #: Name of an environment variable holding an API key, if one is needed.
    api_key_env: str = ""
    #: Query parameter the key is passed as.
    api_key_param: str = "api_key"
    note: str = ""


# ---------------------------------------------------------------------------
# Where each source actually lives
# ---------------------------------------------------------------------------

#: Ordered candidates per source. First usable response wins.
ENDPOINTS: dict[str, tuple[Endpoint, ...]] = {
    "ofac_sdn": (
        Endpoint(
            url="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML",
            expect="xml",
            note="OFAC Sanctions List Service (current host)",
        ),
        Endpoint(
            url="https://www.treasury.gov/ofac/downloads/sdn.xml",
            expect="xml",
            note="legacy download path, still served",
        ),
    ),
    "bis_csl": (
        Endpoint(
            # Bulk file. No key, no rate limit, same content as the search API.
            url="https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json",
            expect="json",
            note="keyless bulk download",
        ),
        Endpoint(
            # Search API. Free key from https://api.trade.gov/ -- set
            # TRADE_GOV_API_KEY and this becomes available automatically.
            url="https://api.trade.gov/consolidated_screening_list/v1/search",
            params={"size": "1000"},
            expect="json",
            api_key_env="TRADE_GOV_API_KEY",
            api_key_param="api_key",
            note="trade.gov search API (needs a free key)",
        ),
    ),
    "eu_fsd": (
        Endpoint(
            url="https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content",
            # Publicly documented constant, not a credential: base64 of "token-2017".
            params={"token": "dG9rZW4tMjAxNw"},
            expect="xml",
            note="EU FSD 1.1 full list",
        ),
    ),
    "federal_register": (
        Endpoint(
            url="https://www.federalregister.gov/api/v1/documents.json",
            expect="json",
            note="Federal Register API v1",
        ),
    ),
}

#: Agency slugs as the Federal Register API expects them.
FR_AGENCY_SLUGS: tuple[str, ...] = (
    "industry-and-security-bureau",
    "foreign-assets-control-office",
)

#: Requesting fields explicitly matters: the default document representation
#: omits `cfr_references` and `docket_ids`, which are two of the three signals
#: the watch module matches on.
FR_FIELDS: tuple[str, ...] = (
    "document_number",
    "title",
    "type",
    "abstract",
    "publication_date",
    "effective_on",
    "agencies",
    "docket_ids",
    "cfr_references",
    "html_url",
)


def federal_register_params(since: date, until: date | None = None) -> dict:
    """Query parameters for the rulemaking window."""
    params: dict = {
        "conditions[publication_date][gte]": since.isoformat(),
        "conditions[agencies][]": list(FR_AGENCY_SLUGS),
        "fields[]": list(FR_FIELDS),
        "per_page": "100",
        "order": "newest",
    }
    if until is not None:
        params["conditions[publication_date][lte]"] = until.isoformat()
    return params


def default_fr_window(today: date, lookback_days: int = 30) -> dict:
    return federal_register_params(today - timedelta(days=lookback_days), today)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def _looks_like(payload: bytes, expect: str) -> bool:
    """Reject an HTML error page served with a 200.

    Government hosts return maintenance notices, WAF challenges and login
    redirects with a success status. Without this check the payload reaches the
    parser, the parser reports zero entries, and the differ reports every entry
    on the list as delisted.
    """
    head = payload.lstrip()[:512].lower()
    if not head:
        return False
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return False
    if expect == "json":
        return head.startswith((b"{", b"["))
    return head.startswith(b"<")


def _get(url: str, params: dict, timeout: int) -> bytes:
    import requests  # optional dependency; only needed for live runs

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.content
        except Exception as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS * attempt)
    raise FetchError(f"{url}: {last_error}") from last_error


def fetch_source(
    source: str,
    extra_params: dict | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> FetchResult:
    """Try each candidate endpoint in order; return the first usable response."""
    candidates = ENDPOINTS.get(source)
    if not candidates:
        raise FetchError(f"no endpoints configured for {source}")

    problems: list[str] = []
    for endpoint in candidates:
        params = {**endpoint.params, **(extra_params or {})}

        if endpoint.api_key_env:
            key = os.environ.get(endpoint.api_key_env, "").strip()
            if not key:
                problems.append(
                    f"{endpoint.url}: skipped, {endpoint.api_key_env} is not set "
                    f"(free key at https://api.trade.gov/)"
                )
                continue
            params[endpoint.api_key_param] = key

        try:
            payload = _get(endpoint.url, params, timeout)
        except FetchError as exc:
            problems.append(str(exc))
            continue

        if not _looks_like(payload, endpoint.expect):
            problems.append(
                f"{endpoint.url}: returned {len(payload)} bytes that are not "
                f"{endpoint.expect} -- probably an error or maintenance page"
            )
            continue

        return FetchResult(source=source, payload=payload, origin=endpoint.url)

    raise FetchError(f"all endpoints failed for {source}:\n  " + "\n  ".join(problems))


def fetch_offline(adapter: SourceAdapter, fixtures: Path, as_of: str, suffix: str) -> FetchResult:
    path = fixtures / adapter.source.split("_")[0] / f"{adapter.source}_{as_of}.{suffix}"
    if not path.exists():
        raise FileNotFoundError(f"no fixture for {adapter.source} at {as_of}: {path}")
    return FetchResult(source=adapter.source, payload=path.read_bytes(), origin=str(path))
