# Restricted-Party Change Monitor

**▶ Live dashboard: [sanctions-delta-monitor-dashboard.vercel.app](https://sanctions-delta-monitor-dashboard.vercel.app/)**

A regulatory monitoring pipeline for the OFAC, BIS and EU restricted-party
lists that answers the question the lists themselves cannot: **when a party is
designated, which other entities became restricted — and which of those appear
on no published list anywhere?**

It polls four primary sources, diffs each publication against the last at the
field level, classifies every change by the regulatory event that produced it,
and then propagates the resulting listed set through an ownership graph under
three separate legal regimes — the OFAC 50 Percent Rule, the BIS Affiliates
Rule, and the EU ownership-or-control test.

```
parse → snapshot → diff → classify → close over ownership → reconcile → brief
```

![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue)
![Tests](https://img.shields.io/badge/tests-126%20passing-green)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-none-green)
![License](https://img.shields.io/badge/license-MIT-green)

**[Open the dashboard](https://almira-halkina.github.io/sanctions-delta-monitor/dashboard/)**: the demo run end to end, with the ownership graph under each regime, the closure pass by pass, every before-and-after movement, the reconciliation record, and a profile of the real lists.

---

## What is real and what is synthetic

The code and the legal rules are real, and the pipeline has been run against the
live regulator files. The worked example used throughout this README, the demo
and the dashboard is a **synthetic scenario**. Every example company, person,
stake and list change in it is invented.

| | Real | Synthetic |
|---|---|---|
| **Code** | Parsers for the OFAC, EU, BIS and Federal Register formats; differ, classifier, ownership closure, reconciliation checks, rulemaking watch | — |
| **Legal rules** | The OFAC 50 Percent Rule, the BIS Affiliates Rule and the EU ownership-or-control test, with their real thresholds, citations and dates, including the Affiliates Rule's reimposition on 10 November 2026 | — |
| **Restricted-party lists** | The live run of 19 August 2026: 19,202 OFAC SDN entries, 6,234 EU entries and 5,308 BIS entries, parsed from the regulators' own files | The two-day demo corpus (`fixtures/`, 3 and 4 August 2026): invented entries in the regulators' exact file formats |
| **List changes** | None yet. The 19 August run was a baseline, see below | The eight changes in the demo: three designations, a delisting, a re-designation, an alias expansion, an identifier enrichment, an address change |
| **Ownership graph** | None yet. The Companies House PSC and GLEIF ingesters exist but no real graph has been built | `fixtures/ownership/`: every company, stake, control right, registry name and filing date |
| **Derived restrictions** | None computed on real data | Everything in [`docs/findings.md`](docs/findings.md): the Volna, Meridian, Aegean, Baltic Marine, Aral and Nemiga cases |
| **Federal Register** | The documents fetched on 19 August 2026. The watch matched one, a BIS rule on drone exports that amends 15 CFR 744 | The two 4 August documents in `fixtures/federal_register/`, including a "request for comment" on the Affiliates Rule. BIS has not published them and the document numbers are invented |
| **Reconciliation** | The failed live run of 18 August 2026, when a namespace change made the OFAC file parse to zero entries and the checks caught it ([design decisions](docs/design-decisions.md)) | The fourteen checks on the demo run |

### Why the demo is synthetic

1. **A real before-and-after didn't exist yet.** Regulators overwrite their
   lists in place and keep no history, so a diff needs two snapshots this
   pipeline archived itself. The first live run, on 19 August 2026, was the
   baseline. Change detection on real data starts from the next live run.
2. **The real ownership graph hasn't been assembled.** The ownership closure
   needs shareholding data. The code can ingest the free sources, but no real
   graph has been built for this repository yet. Without one a live run would
   report zero derived restrictions, which is a false negative rather than a
   finding, so the closure is off by default on live runs.
3. **Naming real companies would be an accusation.** On real data, a derived
   restriction states that a named company is controlled by a sanctioned
   party. Publishing that needs an evidence standard a demo can't meet.
   Invented companies show the method without asserting anything about anyone.
4. **The scenario is built to test every hard case.** It contains each edge
   case exactly once: a two-hop chain, a stake of exactly 50%, stakes that only
   add up across lists, a control right below 50%, an undisclosed stake, a
   delisting that releases subsidiaries, and a promotion that only looks like a
   release. A real day's publications may contain none of them. The tests pin
   the results, so a change to the legal reading fails the build.
5. **It still exercises the real parsers.** The fixtures are generated by code
   in the regulators' wire formats, and CI regenerates them and fails if they
   were edited by hand. The same parsers read the live files: on 19 August they
   parsed exactly the number of entries OFAC and the EU declare in their own
   files.

The [dashboard](docs/dashboard/) labels every section the same way.

---

## Run it in two minutes

No downloads, no API keys, no install step. A synthetic two-day corpus in the
exact wire format of all four sources is committed to the repository.

```bash
git clone https://github.com/almira-halkina/sanctions-delta-monitor
cd sanctions-delta-monitor
python -m regdelta.cli run --date 2026-08-04 --previous 2026-08-03
```

That parses both publications of the SDN list, the BIS Consolidated Screening
List, the EU Consolidated Financial Sanctions List and the Federal Register;
diffs them; runs the ownership closure under all three regimes; reconciles;
and prints the analyst brief. It takes about a second.

```bash
make test        # 126 tests
make fixtures    # regenerate the synthetic corpus
make demo        # the run above
make dashboard   # rebuild docs/dashboard/data.js
```

To run against the real publications, see
[**Running against live data**](#running-against-live-data) below.

---

## Running against live data

The demo above reads committed fixtures. To point it at the actual regulators:

```powershell
python -m pip install requests
python -m regdelta.cli run --live
```

That fetches the current OFAC SDN list (19,202 entries and 28.8 MB as of
18 August 2026), the BIS content of
the Consolidated Screening List, the EU consolidated list, and the last 30 days
of Federal Register rulemaking on the watched CFR parts. Nothing needs an
account:

| Source | Access |
|---|---|
| OFAC SDN | open, no key. Two candidate hosts are tried in order — OFAC has served the list from both through its migration |
| EU consolidated list | open; the `token` in the URL is a publicly documented constant, not a credential |
| Federal Register | open, no key |
| BIS via trade.gov | keyless bulk file first; falls back to the search API if `TRADE_GOV_API_KEY` is set (free from [api.trade.gov](https://api.trade.gov/)). The bulk file is complete on membership but publishes no entity type or structured identifiers for BIS lists — the keyed API does, which is the reason to bother with a key |

### Checking a live run actually worked

The brief reports *change*. On a baseline run there is none, so a correct run
and a silently broken one look similar. `inspect` reads the stored snapshots
back and prints facts that can be checked against the regulators' own pages:

```powershell
python -m regdelta.cli inspect
```

```
ofac_sdn
  publisher's date   08/18/2026
  raw payload        28.8 MB
  entries parsed     19,202
  reconciliation     MATCHES publisher's declared count of 19,202
  with identifiers   6,431 (33%) — these are the ones joinable to a corporate register
  top programmes     RUSSIA-EO14024 (...), SDGT (...), IFSR (...)
```

The reconciliation line is the one that matters: OFAC states a record count in
the file header, the parser counts independently, and either they agree or they
do not. Add `--fixture` to inspect the demo store instead.

**The first live run is a baseline.** There is nothing stored to compare
against, so it captures the current state, says so explicitly, and change
detection begins with the next run. Run it again after the next publication to
get a diff.

**The ownership closure is off by default on live runs.** The committed graph is
keyed to the synthetic corpus and would find no seeds against the real lists,
so reporting a derived set of zero would be a false negative dressed as a
finding. Build a real one from free public data instead:

```powershell
python -m regdelta.cli ownership build --psc psc-snapshot.zip --gleif-rr rr.csv --out ownership
python -m regdelta.cli run --live --ownership ownership
```

See [**Real ownership data**](#real-ownership-data) below.

Three things the live path handles that a naive fetcher does not:

- **A 200 is not necessarily the file.** Government hosts return maintenance
  notices, WAF challenges and login redirects with a success status. A payload
  whose first bytes are not the expected format is rejected as a fetch failure
  — otherwise it reaches the parser, which reports zero entries, and the differ
  reports the entire list as delisted.
- **The namespace is read from the document.** The first live run against the
  Sanctions List Service found `sdnList` served under
  `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML`,
  not the `http://tempuri.org/sdnList.xsd` the published schema declares. A
  parser that hardcodes the documented URI does not error on that — every path
  lookup quietly matches nothing, so a healthy 19,202-entry download parses to
  zero and the differ reports every party on the SDN list as delisted. The
  namespace is now taken from the root element, and a document that really does
  lack `sdnEntry` elements fails with what it contains instead.
- **Failures are per-source.** If the EU webgate is down, the OFAC diff is still
  worth having. The outage is reported as a reconciliation failure naming the
  source, and the run continues. Silently dropping it would turn an outage into
  a false quiet day.
- **The raw bytes are archived.** Regulators overwrite in place and publish no
  history, so a parser bug found in November has to be re-runnable against
  August's payload — the publisher no longer has it.

---

## Real ownership data

The closure needs a graph. Two public datasets assemble into a partial one for
free, and between them they cover the two things it needs — neither covers
both.

| | Companies House PSC | GLEIF Level 2 |
|---|---|---|
| Coverage | UK only | global, entities with an LEI |
| States a percentage? | **yes**, as bands | **no**, ever |
| Cost / registration | free / none | free / none |

That asymmetry is the shape of the problem, not a defect of the sources.
Percentage data is national and patchy; global data is structural.

It also produces the most interesting result in the project. A GLEIF
consolidating-parent edge carries no stake, so under the OFAC and BIS rules it
is an *unrecorded* holding — `indeterminate`, a research queue. Under the EU
test the same edge is `restricted`, because consolidating a subsidiary's
accounts is one of the indicia of control the Council Best Practices list.
**The same relationship, on the same company, is a question in Washington and
an answer in Brussels.** That only becomes visible on real data.

```powershell
python -m regdelta.cli run --live
python -m regdelta.cli ownership build --psc psc-snapshot.zip --gleif-rr rr.csv --gleif-lei lei.csv --out ownership
python -m regdelta.cli run --live --ownership ownership
```

Three decisions in the ingest that would have been wrong the other way:

- **Shares and votes are not summed.** One PSC holding is filed twice, once as
  share ownership and once as voting rights. Adding them turns a single 50–75%
  relationship into 100–150% and manufactures a threshold breach out of a
  filing convention.
- **GLEIF's ultimate parents are not loaded as edges.** If A directly
  consolidates B and C ultimately consolidates B, adding both counts C's
  interest twice — it *runs through* A. Only direct edges are loaded; the
  closure derives the rest. The declared ultimates are kept as a reachability
  check instead, and an ultimate the direct chain cannot reach is reported as a
  hole.
- **Ceased holdings are dropped.** The PSC snapshot retains them. Including one
  would derive a restriction from a shareholding disposed of years ago.

Linking designations to the graph is the step where a mistake is worst.
Everywhere else an error produces a wrong number; here it produces an assertion
that a named real company is controlled by a sanctioned party. So matches are
tiered, only shared identifiers and name-plus-jurisdiction agreement seed the
closure, and everything weaker goes to `links_to_review.csv` with its evidence
rather than silently becoming a finding.

Full detail, including the honest limits, in
[`docs/ownership-data.md`](docs/ownership-data.md).

---

## Why this exists

**On 10 November 2026 the BIS Affiliates Rule comes back into force.**

Published in September 2025 and suspended two months later as part of the
US-China understanding on rare earths, it extends Entity List and Military
End User licence requirements to any entity 50 percent or more owned, in
aggregate, by a listed party — anywhere in the world. Commerce stated in the
preamble that those affiliates will **not** be added to the Entity List.

The consequence is specific and load-bearing. From that date, the Consolidated
Screening List remains a complete record of *listed* parties and becomes an
incomplete record of *restricted* parties. Screening against it is
under-inclusive by construction, and the size of the gap is not published by
anyone.

That gap is what this repository computes.

Two further things follow, and both are why a countdown is not enough. The
suspension was traded for a Chinese concession, so the date is contingent on a
bilateral arrangement rather than a regulatory calendar — `regdelta.watch`
monitors the docket instead of trusting the date. And the same structural
problem already exists under the OFAC 50 Percent Rule and the EU
ownership-or-control test, which have been in force for years and which
disagree with the BIS rule, and with each other, about the same companies.

---

## What a row-count monitor misses

The naive approach compares yesterday's entry count to today's. Most
publication days contain no net change in membership at all. What changes is
the *content* of existing entries.

On the demo corpus, eight changes occur across three sources. A row count sees
three of them.

| Event | What a row count sees | What it actually means |
|---|---|---|
| Alias expansion | nothing | every screening engine now matches two strings it did not match yesterday — hits that did not fire against historical transactions will fire now |
| Re-designation | nothing | the party moved from a sectoral programme to a blocking one: "no new debt over 14 days" became "no dealings at all" |
| Identifier enrichment | nothing | an INN and OGRN were added, so the entity is now joinable to a corporate register — this is the delta that makes its ownership tail computable at all |

So the differ compares fields, not rows, and separates changes that alter what
a screening engine matches from changes that describe an existing target.

---

## What the lists do not say

> **Synthetic example.** The companies and stakes below are from the demo corpus. None of them exist.

One designation in the demo corpus — a Russian holding company — restricts
three further entities that appear on no list anywhere:

| Entity | Jurisdiction | Why | Path |
|---|---|---|---|
| OOO Volna Mashinostroenie | Russia | 75% held by the designated parent | direct |
| Volna Dis Ticaret AS | Türkiye | 60% held by the above | **two hops** |
| Aegean Meridian Holdings Ltd | Cyprus | 50.0% held by the designated parent | direct |

The Turkish subsidiary separates a correct implementation from a plausible one.
Multiplying along the chain gives 75% × 60% = 45%, below the threshold, and an
implementation doing effective-interest arithmetic reports it clean. **The rule
does not multiply.** Once the Russian intermediate is blocked by operation of
the 50 Percent Rule, it *is* a blocked person, and its 60% holding is a blocked
person's 60% holding.

Propagation is therefore a fixed point, not a product — which also makes it
safe on the circular shareholdings common in exactly the structures worth
investigating.

```
restricted = {seeds}
repeat until no change:
    for each entity not yet restricted:
        if sum(stake held by each restricted owner) >= threshold:
            mark restricted
```

---

## Three regimes, one graph, three answers

| | OFAC 50 Percent Rule | BIS Affiliates Rule | EU ownership or control |
|---|---|---|---|
| Threshold | 50% **or more** | 50% **or more** | **more than** 50% |
| Aggregates across | blocked persons | Entity List + MEU + SDN | designated persons |
| Non-percentage control test | no | no | **yes** |
| Consequence | property blocked | licence requirement attaches | funds frozen |
| Status | in force | reimposed 10 Nov 2026 | in force |

Regimes are data, not code, so the same graph runs through all three and the
divergences are reported. They are not academic. Three cases from the synthetic demo corpus:

- A **UAE trading company** held 30% by an SDN and 20% by an Entity List party
  reaches 50% under the Affiliates Rule — which aggregates across lists — and
  under no other rule. Clean under one US regime, restricted under another.
- A **Cypriot holding company** held at exactly 50.0% is caught by "50 percent
  or more" and not by "more than 50%". A group's US arm must block it and its
  EU arm must not.
- A **Lithuanian operator** held 30% by an EU-designated party that can appoint
  and remove its directors is restricted in the EU and clean everywhere else.
  No percentage test finds it.

Full legal reasoning, with citations and what is deliberately *not* modelled,
in [`docs/regimes.md`](docs/regimes.md).

---

## Unknown is not zero

Registers routinely omit percentages. UK PSC filings report bands rather than
numbers; several jurisdictions report nothing at all.

An entity whose known restricted-owner aggregate is below the threshold, but
which has restricted owners holding an unrecorded stake, is returned as
**indeterminate** — a research queue, not a verdict. Collapsing that state into
"clear" is how a wholly-owned subsidiary of a designated parent passes
screening, and it is the most consequential silent failure available in this
problem.

Where a band is available it is read at its floor: "25% to 50%" is taken as
25%, so it does not on its own trip a 50% threshold. Reading the midpoint would
invent a restriction the filing cannot evidence.

---

## Reconciliation runs before the findings, not after

A monitoring pipeline fails quietly. A parser that silently drops half a list
produces thousands of false delistings — each one saying "stop blocking this
party". A fetch that returns a stale file produces a quiet day that is a lie.
Neither raises an exception.

Six checks, each protecting against a specific silent failure:

| Check | Catches |
|---|---|
| `declared_count` | parser drops — OFAC publishes `Record_Count`; a mismatch means the parse is wrong, not the list |
| `publication_advanced` | a re-fetch of yesterday's bytes reported as a quiet day |
| `churn_ceiling` | format changes and truncated downloads (with a size floor: 25% churn on a four-entry list means nothing) |
| `removal_plausibility` | identifier renumbering reported as delisting |
| `graph_coverage` | designated parties with no computable ownership tail |
| `unknown_percent_share` | how much of the graph cannot support a threshold test at all |

If a check fails, the brief says so **above** the findings and states that they
are not safe to act on. An analyst who reads the numbers first and the caveat
second has already acted on the numbers.

---

## Rulemaking watch

Designation feeds cannot answer "did the definition of restricted change".

The Affiliates Rule is the standing example: it added no entries to any list
and expanded the restricted universe by an unknown multiple. A monitor watching
list membership scored that day as quiet.

So the Federal Register is monitored on a separate axis, filtered to the CFR
parts that carry sanctions and export-control rulemaking, against watchpoints
that encode a scheduled regulatory change and the dockets whose activity would
move it:

```
BIS Affiliates Rule reimposed — IMMINENT, 97 days (2026-11-10)

On the current graph this regime would restrict 4 entities that appear on
no published list, with 1 more indeterminate.

Federal Register activity on the watched dockets and CFR parts:
- [Rule] Additions to the Entity List (2026-08-04, effective 2026-08-04)
- [Proposed Rule] Expansion of End-User Controls for Affiliates of Certain
  Listed Entities: Request for Comment (2026-08-04)

A rule or proposed rule touching this docket has published.
Confirm the scheduled date before relying on it.
```

The proposed rule names no entity and changes nothing on any list. It can move
the date on which the entire BIS derived set becomes operative.

> **Synthetic example.** Both Federal Register documents above come from the
> demo fixtures. BIS has not published a request for comment on the Affiliates
> Rule, and the document numbers are invented. On the real live run of
> 19 August 2026, the watch scanned 15 real documents and matched one: *Streamlining
> Export Controls for Drone Exports* (2026-16628, published 14 August 2026),
> because it amends 15 CFR 744. It doesn't affect the Affiliates Rule date, but
> the watch is deliberately broad and flags it for a person to confirm.

---

## Output

Every run writes four artefacts:

| File | For |
|---|---|
| `brief_<date>.md` / `.html` | the analyst — ordered by consequence, not by source |
| `deltas_<date>.jsonl` | machine consumption — one classified change per line |
| `derived_restrictions_<date>.csv` | the screening system — entities restricted by ownership, with the justification chain for each |
| `qa_<date>.json` | the pipeline's own reconciliation record |

Every derived restriction carries its evidence. From the synthetic demo:

```
Volna Dis Ticaret AS, Türkiye — aggregate 60% held by restricted owners
(indirect, 2 hops): OOO Volna Mashinostroenie (RU-VOLNA-MASH) 60%
```

A finding a customer's counsel cannot audit is a finding they cannot act on.

---

## Sources

| Source | Format | Key stability | Notes |
|---|---|---|---|
| OFAC SDN | XML, namespaced | stable — `uid` is never reassigned | `Record_Count` is a free reconciliation target; entities have no `firstName`; aliases carry strong/weak |
| BIS via trade.gov CSL | JSON | **composed** — the publisher's only identifier is a generated digest, so the key is built from list + name + listing date | aggregates eleven lists; only the four BIS ones are taken, so OFAC designations are not double-counted |
| EU FSD 1.1 | XML, namespaced | **unstable** — `logicalId` is reused on re-adoption | one `nameAlias` per language, primary name unflagged |
| Federal Register | JSON | n/a | filtered to 15 CFR 734/736/744 and 31 CFR 548/560/587/589 |

Sources declare their own key stability, and removals from unstable sources are
emitted with `confidence="review"` rather than asserted. A delisting is the one
delta a customer acts on immediately; reporting a renumbering as one is the
fastest way to lose their trust.

Wire-format details and the specific things that break parsers are in
[`docs/data-sources.md`](docs/data-sources.md).

---

## Layout

```
src/regdelta/
  schema.py            canonical record; diffable projection; content hashing
  normalize.py         country, programme taxonomy, transliteration folding
  sources/             one adapter per publisher, parse-only, no network
  snapshot.py          dated store — regulators overwrite in place
  diff.py              field-level differ with per-source removal confidence
  classify.py          regulatory event taxonomy and analyst priority
  ownership/
    graph.py           edges with nullable percentages and control indicators
    closure.py         the three regimes and the fixed-point propagation
    sources/           Companies House PSC and GLEIF Level 2 ingesters
    link.py            tiered matching of designations to graph nodes
    build.py           assemble a real graph and write it out
  watch.py             scheduled regulatory changes and the dockets that move them
  qa.py                reconciliation
  report.py            the brief
  pipeline.py          orchestration — the closure runs twice, before and after
fixtures/generate.py   deterministic synthetic corpus in the real wire formats
scripts/build_dashboard.py  data behind the static dashboard
docs/                  regimes, sources, design decisions, findings
docs/dashboard/        the dashboard (GitHub Pages)
```

~5,200 lines of source, ~1,400 lines of tests. No runtime dependencies for the
offline path; `requests` only for `--live`.

---

## Notes on the fixtures

The committed corpus is **entirely synthetic**. See
[What is real and what is synthetic](#what-is-real-and-what-is-synthetic) for
why, and for which parts of the project use real data. No real person or company is
named, and nothing in this repository should be read as an allegation about
anyone.

It is generated rather than hand-written so that the wire formats are
reproduced exactly, so the corpus is large enough for the reconciliation
thresholds to be meaningful against a realistic denominator, and so the
scenario can be changed and re-run. CI re-runs the generator and fails on any
diff — hand-edited fixtures stop being evidence that the parsers handle the
real formats.

---

## Dashboard

`docs/dashboard/` is a static page with no build step and no dependencies, served by GitHub Pages. Everything on it comes from the pipeline: `scripts/build_dashboard.py` runs the demo, computes the closure under all three regimes before and after, and writes `docs/dashboard/data.js`. If the legal reading in `closure.py` changes, regenerating changes the page with it. Every section of the page is labelled as real data, synthetic demo data, or both.

```bash
make dashboard      # or: python scripts/build_dashboard.py
```

The live-list profile is computed from `data/snapshots/live/` when it exists. That directory is gitignored, so on a fresh clone the profile already committed in `data.js` is kept rather than dropped.

---

## Testing

126 tests, none of which touch the network — the live path is exercised with a
stubbed fetcher. The closure is tested hardest, because that is where the legal
reading is encoded and a quiet change to it would not otherwise fail anything:

```
test_indirect_ownership_is_not_multiplicative
test_stakes_of_separate_blocked_owners_aggregate
test_stakes_of_non_blocked_owners_do_not_count
test_unknown_percentage_is_indeterminate_not_clear
test_circular_shareholding_terminates
test_exactly_fifty_percent_splits_us_from_eu
test_bis_aggregates_entity_list_and_sdn_holdings_together
test_eu_control_test_restricts_below_the_ownership_threshold
test_delisting_releases_the_downstream_subtree
test_psc_bands_are_read_conservatively
```

Plus parser tests against the real wire formats, differ tests for the changes a
row count misses, QA tests for each silent failure mode, and an end-to-end test
that pins the scenario in [`docs/findings.md`](docs/findings.md).

---

## Companion repository

The ownership edges consumed here are the output of
[corporate-ownership-entity-resolution](https://github.com/almira-halkina/corporate-ownership-entity-resolution),
a record-linkage pipeline that resolves UK Companies House PSC filings and
OpenSanctions records into canonical entities. That repository answers *who is
the same party*; this one answers *what follows from designating them*.

---

## Further reading

- [`docs/regimes.md`](docs/regimes.md) — the three regimes, with citations, and what is deliberately not modelled
- [`docs/data-sources.md`](docs/data-sources.md) — wire formats and the things that break parsers
- [`docs/design-decisions.md`](docs/design-decisions.md) — thirteen forks in the road and the
  alternative rejected at each, plus five bugs the first live run found that the fixtures could not
- [`docs/ownership-data.md`](docs/ownership-data.md) — the two free real sources, how to get them, and what each cannot tell you
- [`docs/findings.md`](docs/findings.md) — what the demo run shows, line by line

## License

MIT
