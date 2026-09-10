"""Live-run behaviour, exercised without touching the network.

The fetcher is stubbed, so these tests cover the parts that go wrong in
practice -- an error page served with a 200, a source that is down, a first run
with nothing to compare against -- rather than the HTTP call itself.
"""

from __future__ import annotations

from datetime import date

import pytest

from regdelta import fetch as fetch_mod
from regdelta.config import Paths
from regdelta.fetch import (
    ENDPOINTS,
    FetchError,
    FetchResult,
    _looks_like,
    default_fr_window,
    fetch_source,
)
from regdelta.pipeline import FIXTURE_SUFFIX, run_live
from regdelta.qa import Severity

# -- payload sniffing -------------------------------------------------------

@pytest.mark.parametrize("payload,expect,ok", [
    (b'<?xml version="1.0"?><sdnList/>', "xml", True),
    (b'  {"results": []}', "json", True),
    (b"<!DOCTYPE html><html><body>Service unavailable</body></html>", "xml", False),
    (b"<html><head><title>Login</title></head></html>", "json", False),
    (b"", "xml", False),
    (b'{"results": []}', "xml", False),
])
def test_error_pages_served_with_200_are_rejected(payload, expect, ok):
    """A maintenance page reaching the parser reads as every entry delisted."""
    assert _looks_like(payload, expect) is ok


# -- endpoint selection -----------------------------------------------------

def test_every_source_has_at_least_one_endpoint():
    for source in ("ofac_sdn", "bis_csl", "eu_fsd", "federal_register"):
        assert ENDPOINTS[source]


def test_ofac_has_a_fallback_host():
    """OFAC has served the SDN list from two hosts through the migration."""
    assert len(ENDPOINTS["ofac_sdn"]) >= 2


def test_keyed_endpoint_is_skipped_when_the_key_is_absent(monkeypatch):
    monkeypatch.delenv("TRADE_GOV_API_KEY", raising=False)
    monkeypatch.setattr(fetch_mod, "_get", lambda *a, **k: (_ for _ in ()).throw(FetchError("down")))
    with pytest.raises(FetchError) as excinfo:
        fetch_source("bis_csl")
    message = str(excinfo.value)
    assert "TRADE_GOV_API_KEY is not set" in message
    assert "api.trade.gov" in message  # tells the user how to fix it


def test_federal_register_query_requests_the_fields_the_watch_needs():
    """cfr_references and docket_ids are omitted from the default representation."""
    params = default_fr_window(date(2026, 8, 18), lookback_days=30)
    assert params["conditions[publication_date][gte]"] == "2026-07-19"
    assert "cfr_references" in params["fields[]"]
    assert "docket_ids" in params["fields[]"]
    assert "industry-and-security-bureau" in params["conditions[agencies][]"]


# -- run_live ---------------------------------------------------------------

def _stub_fetcher(fixtures, day, broken=()):
    def fetch(source, extra_params=None, timeout=None):
        if source in broken:
            raise FetchError(f"{source}: simulated outage")
        if source == "federal_register":
            path = fixtures / "federal_register" / "federal_register_2026-08-04.json"
        else:
            path = fixtures / {"ofac_sdn": "ofac", "bis_csl": "bis", "eu_fsd": "eu"}[source] / (
                f"{source}_{day}.{FIXTURE_SUFFIX[source]}"
            )
        return FetchResult(source=source, payload=path.read_bytes(), origin=f"stub://{source}")

    return fetch


def test_first_run_is_a_baseline_and_says_so(fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-03"))
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    result = run_live(paths=paths, today=date(2026, 8, 3))

    assert result.brief.deltas == []
    baselines = [c for c in result.qa.checks if c.name == "baseline"]
    assert len(baselines) == 3
    assert all(c.severity is Severity.WARN for c in baselines)
    assert "Change detection begins with the next publication" in baselines[0].message


def test_second_run_diffs_against_the_stored_snapshot(fixtures_dir, tmp_path, monkeypatch):
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-03"))
    run_live(paths=paths, today=date(2026, 8, 3))

    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-04"))
    result = run_live(paths=paths, today=date(2026, 8, 4))

    kinds = {d.event_type.value for d in result.brief.deltas}
    assert "new_designation" in kinds
    assert "alias_expansion" in kinds


def test_raw_payloads_are_archived_for_replay(fixtures_dir, tmp_path, monkeypatch):
    """Regulators overwrite in place; the bytes are gone once replaced."""
    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-04"))
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    run_live(paths=paths, today=date(2026, 8, 4))

    archived = sorted(p.name for p in (tmp_path / "s" / "live" / "raw").rglob("*.*"))
    assert "ofac_sdn_2026-08-04.xml" in archived
    assert "federal_register_2026-08-04.json" in archived


def test_a_source_outage_is_a_named_failure_not_a_quiet_day(fixtures_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(
        fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-04", broken={"eu_fsd"})
    )
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    result = run_live(paths=paths, today=date(2026, 8, 4))

    failures = [c for c in result.qa.checks if c.severity is Severity.FAIL]
    assert any("eu_fsd" in c.message for c in failures)
    assert any("says nothing about it" in c.message for c in failures)
    # and the other sources still produced a run
    assert "ofac_sdn" in {c.message.split(":")[0] for c in result.qa.checks if c.name == "fetch"}


def test_watch_still_runs_when_every_list_fetch_fails(fixtures_dir, tmp_path, monkeypatch):
    """A rule that names nobody is exactly what the feeds cannot show."""
    monkeypatch.setattr(
        fetch_mod,
        "fetch_source",
        _stub_fetcher(fixtures_dir, "2026-08-04", broken={"ofac_sdn", "bis_csl", "eu_fsd"}),
    )
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    result = run_live(paths=paths, today=date(2026, 8, 18))

    assert result.brief.watch[0].days_remaining == 84
    assert result.brief.watch[0].date_may_have_moved


def test_ownership_closure_is_skipped_without_a_graph(fixtures_dir, tmp_path, monkeypatch):
    """Reporting a derived set of zero would be a false negative dressed as a finding."""
    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-04"))
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    result = run_live(paths=paths, today=date(2026, 8, 4))

    assert result.closures_after == {}
    assert any("ownership closure not run" in note for note in result.brief.source_notes)


def test_ownership_closure_runs_when_a_graph_is_supplied(fixtures_dir, tmp_path, monkeypatch):
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-03"))
    run_live(paths=paths, today=date(2026, 8, 3), ownership_dir=fixtures_dir / "ownership")

    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-04"))
    result = run_live(paths=paths, today=date(2026, 8, 4), ownership_dir=fixtures_dir / "ownership")

    assert set(result.brief.new_derived["ofac_50pct"]) == {
        "RU-VOLNA-MASH", "TR-VOLNA-DIS", "CY-AEGEAN"
    }


def test_live_and_fixture_snapshots_never_share_a_store(fixtures_dir, tmp_path, monkeypatch):
    """Regression: a live run once diffed the real EU list against a fixture.

    The demo writes synthetic snapshots; a live run then found them as "the
    previous publication" and reported every real designation as new and every
    synthetic entry as delisted. Two corpora that share a key space but not a
    universe must never be compared.
    """
    from regdelta.pipeline import run

    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    run("2026-08-04", "2026-08-03", paths=paths, today=date(2026, 8, 4))
    monkeypatch.setattr(fetch_mod, "fetch_source", _stub_fetcher(fixtures_dir, "2026-08-04"))
    result = run_live(paths=paths, today=date(2026, 8, 19))

    assert (tmp_path / "s" / "fixture").is_dir()
    assert (tmp_path / "s" / "live").is_dir()
    # The live run must treat 2026-08-19 as its first observation, not diff it
    # against the fixture snapshots sitting in the other store.
    assert [c for c in result.qa.checks if c.name == "baseline"]
    assert result.brief.deltas == []


def test_an_unparseable_payload_is_still_archived(fixtures_dir, tmp_path, monkeypatch):
    """The payload that failed is the evidence; the publisher will overwrite it."""
    def broken_fetch(source, extra_params=None, timeout=None):
        if source == "ofac_sdn":
            return FetchResult(source, b"<sdnList><somethingElse/></sdnList>", "stub://ofac")
        return _stub_fetcher(fixtures_dir, "2026-08-04")(source, extra_params, timeout)

    monkeypatch.setattr(fetch_mod, "fetch_source", broken_fetch)
    paths = Paths(fixtures=fixtures_dir, snapshots=tmp_path / "s", output=tmp_path / "o")

    result = run_live(paths=paths, today=date(2026, 8, 19))

    archived = tmp_path / "s" / "live" / "raw" / "ofac_sdn" / "ofac_sdn_2026-08-19.xml"
    assert archived.exists()
    failure = next(c for c in result.qa.checks if c.severity is Severity.FAIL)
    assert "Payload kept at" in failure.message
    assert "did not parse" in failure.message
