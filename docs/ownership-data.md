# Real ownership data

The closure needs an ownership graph. Commercial providers sell one; two public
datasets can be assembled into a partial substitute for free, and between them
they cover the two things the closure needs. Neither covers both.

| | Companies House PSC | GLEIF Level 2 |
|---|---|---|
| Cost | free | free |
| Registration | none | none |
| Coverage | UK companies only | global, entities inside the LEI system |
| States a percentage? | **yes**, as bands | **no**, ever |
| Update cadence | daily | daily |
| Size | ~2 GB, ~12M records | ~100 MB relationships |

That asymmetry is the shape of the problem, not a defect of the sources.
Percentage data is national and patchy; global data is structural.

## Getting the files

**Companies House PSC snapshot** —
[download.companieshouse.gov.uk/en_pscdata.html](http://download.companieshouse.gov.uk/en_pscdata.html).
Take the single-file ZIP. Updated before 10am GMT each day, compiled to the end
of the previous day.

**GLEIF Level 2** —
[gleif.org concatenated files](https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file).
Take the RR-CDF file for relationships. The LEI-CDF (Level 1) file is optional
and supplies entity names and countries; without it the graph is correct but
its nodes are bare LEIs, which makes a brief unreadable.

## Building the graph

```bash
python -m regdelta.cli run --live          # populate the snapshot store first
python -m regdelta.cli ownership build \
    --psc psc-snapshot.zip \
    --gleif-rr rr-golden-copy.csv \
    --gleif-lei lei-golden-copy.csv \
    --out ownership
python -m regdelta.cli run --live --ownership ownership
```

`--limit N` stops after N source records, which is the sane way to see the
shape of the output before committing to a full pass over twelve million rows.

The build writes four files:

| File | Contents |
|---|---|
| `nodes.csv`, `edges.csv` | the graph, in the same format the fixture graph uses |
| `links.jsonl` | matches that seeded the closure, with evidence |
| `links_to_review.csv` | matches too weak to act on, kept for a human |

The two CSVs are deliberately the same format as the synthetic fixture graph.
If the pipeline needed a different code path for real data, the demo would stop
being evidence that the real path works.

## What each source contributes to the closure

**Companies House gives bands**, and a band can trip a threshold. A designated
party holding 50–75% of a UK company produces a `RESTRICTED` verdict under all
three regimes. A 25–50% band, read at its floor, produces nothing on its own —
which is correct, because that filing does not evidence control.

**GLEIF gives structure with no percentage.** A consolidating-parent edge is an
*unrecorded* holding, so:

- under the OFAC 50 Percent Rule and the BIS Affiliates Rule the subsidiary is
  `INDETERMINATE` — a research queue, not a verdict;
- under the EU test it is `RESTRICTED`, because consolidating a subsidiary's
  financial statements is one of the indicia of control the Council Best
  Practices list, and control alone is sufficient there.

The same GLEIF edge therefore produces "needs research" in Washington and
"restricted" in Brussels. That divergence is real and only becomes visible on
real data.

## Decisions that would have been wrong

**Summing shares and votes.** A single PSC holding is normally filed twice,
once as share ownership and once as voting rights. Adding them turns one
50–75% relationship into 100–150% and manufactures a threshold breach out of a
filing convention. The maximum band is taken, not the sum.

**Loading GLEIF's ultimate parents as edges.** The file states both direct and
ultimate consolidation. If A directly consolidates B and C ultimately
consolidates B, adding both gives B two owners in the aggregation step — when
C's interest *runs through* A and is the same interest counted twice. Only
direct relationships become edges; the closure derives the ultimate ones by
iterating, which is what it is for. The declared ultimates are still read and
used as a reachability check: an ultimate parent the direct chain cannot reach
is a hole in the graph, and the ingest reports the count.

**Keeping ceased PSC holdings.** The snapshot retains records with `ceased_on`
set. Including them would derive a restriction from a shareholding disposed of
years ago.

**Treating statements as owners.** The PSC file interleaves `psc-statement`
records — "no PSC identified", "details withheld", exemption notices. They
carry no owner. They are a genuine opacity signal and worth analysing
separately, but they are not ownership edges.

## Linking designations to the graph

Covered in full in the module docstring of `regdelta/ownership/link.py`. The
short version, because it is the step where a mistake is worst:

Everywhere else in this package, an error produces a wrong number. Here an
error produces an assertion that **a named real company is controlled by a
sanctioned party**. A false negative is a coverage gap the reconciliation
checks already report. A false positive is a defamatory claim.

So matches are tiered and only the top two seed the closure:

| Tier | Basis | Seeds? |
|---|---|---|
| `identifier` | shared LEI or registration number | yes |
| `name_and_country` | normalised names and jurisdictions both agree | yes |
| `name_only` | names agree, jurisdictions do not, or the name is ambiguous | no |
| `transliteration` | only the folded transliteration keys agree | no |

Weak matches are not discarded — a sanctioned party behind a transliteration
variant is exactly the case worth investigating. They go to
`links_to_review.csv` rather than silently becoming findings.

## Honest limits

- **Coverage is partial and unevenly so.** Most designated parties will match
  nothing. `check_graph_coverage` reports the ratio, and every derived count is
  a floor rather than a total.
- **UK-only percentages.** Everything outside the UK arrives without a stake,
  so US-side findings skew heavily toward UK structures. That is a property of
  what is published for free, not of the method.
- **Individuals collide.** Companies House redacts the day of birth, so an
  individual PSC is identified by name plus birth month and year. Two people
  sharing both will merge. Individual-derived findings deserve more scepticism
  than corporate ones.
- **LEI coverage is self-selected.** Entities obtain LEIs for financial-market
  reasons. Structures built to avoid scrutiny are systematically less likely to
  appear — which is the opposite of where you would want coverage to be
  strongest.
