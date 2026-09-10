# What the demo run shows

`make demo` compares the publications of 2026-08-03 and 2026-08-04 across
OFAC, BIS and the EU, runs the resulting listed sets through the ownership
graph under all three regimes, and writes the brief.

The corpus is synthetic. No real person or company is named; nothing here is an
allegation about anyone. It is built so that every path the pipeline claims to
handle occurs exactly once, and so the numbers below are pinned by
`tests/test_pipeline.py` — a refactor that quietly changes the legal reading
fails the build.

## The published feeds

Eight changes across three sources. A row-count monitor would have seen three.

| Event | Entity | Source | What a row count sees |
|---|---|---|---|
| New designation | PAO Volna Holding | OFAC | a new row |
| New designation | Kaspiy Precision Machining LLP | BIS Entity List | a new row |
| New designation | OAO Nemiga Optics | EU | a new row |
| Delisting | Siarhei Karpenka | OFAC | a missing row |
| Re-designation | AO Sevastopol Marine Engineering | OFAC | **nothing** |
| Alias expansion | Yevgeniy Zhuravlyov | OFAC | **nothing** |
| Identifier enrichment | OOO Titan Logistika | OFAC | **nothing** |
| Administrative | ZAO Nevsky Pribor | OFAC | **nothing** |

Seven of the eight change which strings a screening engine matches.

Three are worth calling out:

**The re-designation** moves AO Sevastopol Marine Engineering from
`UKRAINE-EO13662` to `RUSSIA-EO14024` — sectoral to blocking. Same name, same
key, and the difference between "no new debt over 14 days" and "no dealings at
all".

**The alias expansion** adds `Evgenii Juravlev` and `Yevgeniy Zhuravlyow` to an
existing entry. List membership is unchanged. Every screening system now
matches two strings it did not match yesterday, which means hits that did not
fire against historical transactions will fire now. The transliteration
folding in `normalize.py` collapses all four spellings to one key.

**The identifier enrichment** adds an INN and OGRN to OOO Titan Logistika. This
is the delta that makes an entity joinable to a corporate register, and
therefore the delta that makes its ownership tail computable at all. It is
invisible to every monitor that watches names.

## What the feeds do not say

One OFAC designation — PAO Volna Holding — restricts three further entities
that appear on no list anywhere:

| Entity | Jurisdiction | Why | Path |
|---|---|---|---|
| OOO Volna Mashinostroenie | Russia | 75% held by the designated parent | direct |
| Volna Dis Ticaret AS | Türkiye | 60% held by the above | **two hops** |
| Aegean Meridian Holdings Ltd | Cyprus | 50.0% held by the designated parent | direct |

The Turkish subsidiary is the case that separates a correct implementation from
a plausible one. Multiplying along the chain gives 75% × 60% = 45%, which is
below the threshold, and a monitor doing effective-interest arithmetic reports
it clean. The rule does not multiply: once the Russian intermediate is blocked
it *is* a blocked person, and its 60% is a blocked person's 60%.

## Where the regimes disagree

| Entity | OFAC | BIS Affiliates | EU |
|---|---|---|---|
| Meridian General Trading FZE (UAE) | clear | **restricted** | clear |
| Aegean Meridian Holdings Ltd (Cyprus) | **restricted** | **restricted** | clear |
| Baltic Marine Operations UAB (Lithuania) | clear | clear | **restricted** |
| Aral Trading LLP (Kazakhstan) | indeterminate | indeterminate | clear |

**Meridian General Trading FZE** is 30% held by the new SDN and 20% held by an
Entity List party. Neither reaches 50% alone, and OFAC's rule aggregates only
across blocked persons — the Entity List party is not one. The Affiliates Rule
aggregates Entity List, MEU and SDN holdings together, so it reaches 50% there
and nowhere else. A UAE trading company that is clean under one US rule and
restricted under another.

**Aegean Meridian Holdings Ltd** is held at exactly 50.0%. "50 percent or more"
catches it; "more than 50%" does not. One word of legal text, and a Cypriot
holding company that a group's US arm must block and its EU arm must not.

**Baltic Marine Operations UAB** is 30% held by an EU-designated party that
also holds the right to appoint and remove directors. No percentage test finds
this. The EU's control limb does.

**Aral Trading LLP** has a restricted owner whose stake the Kazakh register
does not disclose, plus a 15% holding from another restricted party. Known
aggregate is 15%. It cannot be cleared and cannot be restricted from the
register alone, so it goes to the research queue rather than into either
column.

## What a delisting releases

Siarhei Karpenka comes off the SDN list. Two Belarusian entities — OAO Nemiga
Optics and its wholly-owned Nemiga Trade House OOO — were restricted *solely*
through his 80% holding. Both are now clear under the US regimes, and no
published feed says so. Continuing to block them is its own compliance failure.

The same day, the EU designates OAO Nemiga Optics directly. So the entity moves
from US-derived-restricted to US-clear and simultaneously from EU-clear to
EU-listed, and its subsidiary becomes EU-restricted by ownership. The brief
reports both movements against the same company on the same day.

One case that looks like a release and is not: Kaspiy Precision Machining LLP
was derived-restricted yesterday through its 55% Entity List parent, and is
*named on the Entity List* today. That is a promotion, not a release. Reporting
it as a release would tell a customer to unblock an explicitly listed party.

## The rulemaking watch

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

The proposed rule names no entity. It changes nothing on any list. It is
capable of moving the date on which the entire BIS derived set becomes
operative, and it is the reason the watch module exists.

## Reconciliation

Fourteen checks across three sources on this run: thirteen pass, one warns.

```
ok    declared_count       ofac_sdn: parsed 255 entries, matching the publisher's declared count
ok    publication_advanced ofac_sdn: publication advanced 08/03/2026 -> 08/04/2026
ok    churn_ceiling        ofac_sdn: 2.35% of entries changed, within the 5% ceiling
ok    removal_plausibility ofac_sdn: 1 removals, within plausible range
warn  graph_coverage       6/260 listed parties have a node in the ownership graph;
                           254 have no computable ownership tail
ok    unknown_percent_share 1/13 ownership edges (7.7%) carry no percentage
ok    churn_ceiling        bis_csl: 1 of 2 entries changed; below the 100-entry floor
                           where a churn ratio is meaningful, test not applied
```

The warning is the honest one. Most designated parties in the corpus have no
node in the ownership graph, so most have no computable tail. The derived
findings above are a floor, not a total, and the brief says so on its face
rather than presenting a number that looks complete.
