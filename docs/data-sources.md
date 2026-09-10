# Sources, wire formats and the things that break parsers

Four publishers, four shapes, no agreement on field names, identifier schemes,
country encodings or update cadence. Everything below is reproduced exactly in
`fixtures/generate.py`, so the parsers are exercised against the same byte
shapes the regulators actually emit.

## OFAC — Specially Designated Nationals

| | |
|---|---|
| Endpoint | `sanctionslistservice.ofac.treas.gov/api/publicationpreview/exports/SDN.XML` |
| Format | XML, namespace `http://tempuri.org/sdnList.xsd` |
| Key | `uid`, **stable** — never reassigned |
| Cadence | irregular; several publications a week during active periods |
| Scale | ~17,000 entries |

Things that break parsers:

- **The namespace is on every element.** A parser written against a
  namespace-stripped sample returns zero entries against the real file and,
  because zero entries diffed against yesterday is 17,000 delistings, does so
  loudly. `OfacSdnAdapter` raises rather than returning an empty snapshot.
- **`publshInformation` is misspelled** in the schema. It is load-bearing; it
  carries `Publish_Date` and `Record_Count`.
- **`Record_Count` is a free reconciliation target.** If the parse count does
  not equal the declared count, the parse is wrong. `check_declared_count`
  makes that a build failure rather than a silent one.
- **Entities have no `firstName`.** The element is absent, not empty. Treating
  absence as a blank given name types every company as a person.
- **Aliases carry `category` = `strong` or `weak`.** Weak aliases are published
  for investigative context and are explicitly not intended for automated
  screening. They are retained and tagged inline, because the count of *strong*
  aliases is what actually moves a screening engine's recall.
- **Countries are prose**, and inconsistent prose: `Russia`, `Korea, North`,
  `Virgin Islands, British`. Normalised to ISO alpha-2, with unrecognised
  values returned empty rather than guessed.
- **Multi-valued fields are not order-stable** between publications. Sorted at
  parse time, otherwise a permuted alias list reads as an amendment.

## BIS — via the trade.gov Consolidated Screening List

| | |
|---|---|
| Endpoint | `data.trade.gov/consolidated_screening_list/v1/search` |
| Format | JSON |
| Key | `id`, **unstable** — the MEU list has been republished wholesale |
| Cadence | daily |
| Scale | ~13,000 entries across eleven lists |

- **The CSL aggregates eleven lists, including OFAC's.** This adapter keeps
  only the four BIS-administered ones. Taking OFAC content from both the SDN
  XML and the CSL emits two deltas for one designation, which an analyst then
  de-duplicates by hand. `test_csl_adapter_ignores_non_bis_lists` pins it.
- **`source` is a long descriptive label**, not a code — `"Entity List (EL) -
  Bureau of Industry and Security"`. Match on substrings; equality breaks when
  trade.gov edits the label.
- **There is no business identifier.** The only per-record id is a
  56-hex-character digest trade.gov generates; BIS's own `entity_number` does
  not appear in the file. If that digest is content-derived — its shape
  suggests it is — a differ keyed on it reports an added alias as a delisting
  plus a new designation, which is the worst direction to be wrong in. The key
  is therefore composed from list + normalised name + listing date: the fields
  that identify the party rather than describe it. The publisher's digest is
  carried through as an identifier so that, if it does churn on unchanged
  records, the diff shows it.
- **The keyless bulk file is thinner than the keyed API.** Observed 2026-08-19
  across 25,942 records: `type` and `ids` are present on the ~19,700
  SDN-shaped records and absent entirely from BIS ones. So entity type and
  structured identifiers are simply not published for Entity List, MEU, UVL and
  DPL entries in the bulk download. The adapter records `entity_type =
  "not-published"` rather than `"unknown"`, because "the publisher does not
  say" and "we could not work it out" call for different responses.
- **`federal_register_notice`** is the only field tying a listing back to the
  rulemaking that created it, which is what lets the watch module connect a
  designation to a docket.

The reason this feed's importance changes on 10 November 2026 is in
[`regimes.md`](regimes.md): affiliates caught by the Affiliates Rule are not
added to the Entity List, so the CSL stops being a sufficient screening input
on that date.

## EU — Consolidated Financial Sanctions List

| | |
|---|---|
| Endpoint | `webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content` |
| Format | XML (FSD 1.1), namespace `http://eu.europa.ec/fpi/fsd/export` |
| Key | `logicalId`, **unstable** — reused on re-adoption under a new regulation |
| Cadence | on publication of each amending regulation |
| Scale | ~3,000 entities |

- **One entity carries many `nameAlias` children**, one per language variant.
  The primary name is not flagged; convention is the first English-language
  `wholeName`. EU entries therefore carry far more aliases than OFAC ones,
  which is why alias-count reconciliation has to be per-source rather than
  global.
- **`subjectType/@classificationCode`** is `P` for person, `E` for enterprise.
- **`programme` lives on `regulation`,** not on the entity, and an entity can
  carry several regulations.

## Federal Register

| | |
|---|---|
| Endpoint | `federalregister.gov/api/v1/documents.json` |
| Format | JSON |
| Cadence | daily |

Watched CFR parts, and why, are in
`src/regdelta/sources/federal_register.py`:

| Part | Why |
|---|---|
| 15 CFR 744 | EAR end-user controls: Entity List, MEU List, Affiliates Rule |
| 15 CFR 734 | EAR scope and de minimis |
| 15 CFR 736 | EAR General Prohibitions |
| 31 CFR 587 | OFAC Russian Harmful Foreign Activities |
| 31 CFR 589 | OFAC Ukraine-Related |
| 31 CFR 548 | OFAC Belarus |
| 31 CFR 560 | OFAC Iran |

This feed exists because designation feeds cannot answer "did the definition of
restricted change". The Affiliates Rule added no entries to any list and
expanded the restricted universe by an unknown multiple; a monitor watching
only list membership scored that day as quiet.

## Ownership edges

Not a regulator feed. Edges come from corporate registers — UK Companies House
PSC filings, EU business registers, commercial aggregations — *after* the
register records have been resolved to canonical entities. Resolution is not
done here; this package consumes an already-resolved edge list.

The fields that matter:

- `percent` may be null. Null propagates as unknown, never as zero.
- `band` accepts Companies House PSC bands, read at their floor.
- `control_indicators` carries the non-percentage signals the EU control test
  needs and the US rules ignore.
- `source` and `as_of` are carried so the brief can distinguish a restriction
  derived from last week's filing from one derived from a filing three years
  stale.

## Fetching

`regdelta.fetch` is the only module that imports `requests`, and it is an
optional dependency. Every parser and every downstream stage runs identically
against a committed fixture and a live download, which is what makes the
repository reviewable offline and what makes a bad publication day replayable
rather than lost.

Live retrieval (`regdelta run --live`) adds three behaviours that only matter
against real endpoints:

- **Ordered candidate URLs per source.** OFAC has served the SDN list from both
  `treasury.gov/ofac/downloads` and the Sanctions List Service host through its
  migration. The first candidate returning usable bytes wins, so a publisher
  reorganising its file server does not produce a false quiet day.
- **Payload sniffing.** Government hosts return HTML error pages with a 200
  status. A payload whose first bytes are not the expected format is a fetch
  failure, not a parse failure reported against 17,000 missing entries.
- **Per-source failure isolation.** An unreachable source is recorded as a
  `FAIL`-severity reconciliation check naming that source, and the run
  continues with the others. The Federal Register watch runs even when every
  list fetch fails, because a rule that names nobody is exactly the change the
  designation feeds cannot show.
