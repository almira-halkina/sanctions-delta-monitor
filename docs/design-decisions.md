# Design decisions

Each of these was a fork in the road. The alternative is stated, because the
reason for the choice is only legible next to what was rejected.

## 1. Diff fields, not rows

**Alternative:** compare yesterday's entry count to today's.

Most publication days contain no net change in membership. What changes is the
*content* of existing entries — an alias added, a programme moved, a
registration number appended. A row-count monitor reports those days as quiet.

An alias addition is the case that matters most and looks like nothing: list
membership is identical, and every screening engine in the world now matches a
string it did not match yesterday. That is a recall change, and it means hits
that did not fire against last month's transactions will fire now.

So the differ compares the diffable projection of each record and reports
*which fields* moved. `SCREENING_RELEVANT_FIELDS` separates changes that alter
what a screening engine matches from changes that describe an existing target.

## 2. Sort multi-valued fields at parse time

**Alternative:** compare lists as published.

Sanctions lists are not order-stable. The same entry comes back with its
aliases permuted for no reason anyone outside the publisher can see. Without
sorting, a cosmetic reordering is reported to an analyst as a substantive
amendment, and after the third one they stop reading the section.

## 3. Declare key stability per source, and downgrade removals accordingly

**Alternative:** treat every disappeared key as a delisting.

OFAC's `uid` is never reassigned. The EU's `logicalId` is reused when an entity
is re-adopted under a new regulation. Some BIS sub-lists have been republished
wholesale with new identifiers.

A delisting is the one delta a customer acts on immediately, and acting on a
false one means unblocking a party that is still designated. So adapters
declare `key_stability`, and removals from unstable sources are emitted with
`confidence="review"` rather than suppressed or asserted.

## 4. Propagate restriction by fixed point, not by multiplying percentages

**Alternative:** effective-interest arithmetic — 60% of 60% is 36%.

This is the single most common way an implementation of the 50 Percent Rule
gets it wrong, and the error always runs the same way: it under-reports. Once
an entity is blocked by operation of the rule it *is* a blocked person, and its
holdings count at face value. Full reasoning in [`regimes.md`](regimes.md).

Iteration also makes the traversal safe on circular shareholdings, which a
recursive descent is not.

## 5. Unknown ownership is a third state

**Alternative:** treat a missing percentage as zero, or as 100%.

Zero clears wholly-owned subsidiaries of designated parents. One hundred
manufactures restrictions that no filing evidences. `INDETERMINATE` is a
research queue: it cannot be cleared and cannot be restricted from the register
alone, and saying so is more useful than a confident wrong answer in either
direction.

`check_unknown_percent_share` reports what fraction of the graph is in that
condition, which bounds how much confidence the derived set deserves.

## 6. Read ownership bands at their floor

**Alternative:** read the midpoint.

A Companies House PSC filing of "25% to 50%" read at its midpoint is 37.5%,
which sums with a second such holding to 75% and restricts an entity on the
strength of two bands. Read at their floors they sum to 50% and restrict it on
the strength of what the filings actually say. Conservative in the direction of
under-claiming, which is the correct direction for a finding that has to be
defensible to a customer's counsel.

## 7. Regimes are data

**Alternative:** one hard-coded 50% rule.

Three regimes govern the same corporate structures and disagree — on the
threshold operator, on which lists aggregate, on whether a non-percentage
control test exists. Encoding them as `Regime` records means the same graph
runs through all three and `divergences()` reports the entities a multinational
cannot cover with a single policy. Adding the UK's OFSI test is a dict entry,
not a code change.

## 8. Compute the closure twice — before and after

**Alternative:** compute today's derived set and report it.

The useful statement is not "N entities are restricted", it is "N entities
*became* restricted today because of this designation". That requires the
counterfactual, and the counterfactual is yesterday's listed set run through
the same graph.

It also catches the case people forget: a delisting can release an entire
downstream subtree that was restricted solely through the delisted parent. No
published feed says so, and continuing to block those parties is its own
compliance failure.

One subtlety, pinned by
`test_promotion_from_derived_to_listed_is_not_reported_as_a_release`: an entity
that was derived yesterday and is *named on a list* today has not been
released. It has been promoted. Reporting that as a release would tell a
customer to unblock an explicitly designated party.

## 9. Fail loudly on a partial parse

**Alternative:** best-effort parsing, skip malformed entries.

A parser that drops half a list produces thousands of false delistings, and
every one of them says "stop blocking this party". In a screening context that
is the expensive direction to be wrong in. `ParseError` is fatal, and
`check_declared_count` turns OFAC's own `Record_Count` into an independent
assertion that nothing was dropped.

## 10. Reconciliation appears above the findings, not below

**Alternative:** a QA appendix.

An analyst who reads the numbers first and the caveat second has already acted
on the numbers. If a check failed, the brief says so before it says anything
else, and says that the findings below are not safe to act on.

## 11. Churn thresholds have a size floor

**Alternative:** apply the ratio everywhere.

One amendment on a four-entry list is 25% churn and means nothing. Several BIS
sub-lists and some EU programme lists are genuinely that small. A check that
fires on them every day is a check an analyst learns to ignore, which is worse
than not having it. Below 100 entries the proportional test reports the raw
count and declines to judge.

## 12. Fixtures are generated, not hand-written

**Alternative:** paste a few real entries into an XML file.

Generated fixtures reproduce the wire formats exactly, are large enough that
the reconciliation thresholds are exercised against a realistic denominator,
and are regenerable when the scenario changes. CI re-runs the generator and
fails on any diff, so the committed corpus cannot drift into being hand-edited
— and hand-edited fixtures stop being evidence that the parsers handle the real
formats.

They are also entirely synthetic. No real person or company is named. Nothing
in this repository should be read as an allegation about anyone.

## 13. No dependencies in the hot path

**Alternative:** lxml, pandas, networkx, a markdown library.

The parsers, the closure and the brief run on the standard library. `requests`
is optional and only needed to fetch live publications. The repository can be
cloned and run with no install step, which is what makes it reviewable in the
two minutes a reviewer will actually spend.

---

# Found against live data

Everything above was decided before the pipeline had seen a real publication.
The first live run — 19 August 2026, against OFAC, trade.gov and the EU
webgate — found four things the fixtures could not have. They are recorded
here because the *shape* of these failures is the interesting part: three of
the four produce wrong answers silently, and only one of them looks like an
error at the time it happens.

## 1. The namespace is not the documented namespace

OFAC's published schema declares `http://tempuri.org/sdnList.xsd`. The
Sanctions List Service serves the same element structure under
`https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/XML`.

A parser that hardcodes the documented URI does not raise. Every
namespace-qualified path simply matches nothing, so a healthy 28.8 MB download
carrying 19,202 records parses to zero entries — and zero entries diffed
against yesterday is **the entire SDN list reported as delisted**. In a
screening context that is the most expensive direction to be wrong in: it tells
a customer to stop blocking everybody.

Fixed by reading the namespace off the root element and qualifying paths with
whatever the document declares, empty included. The observed URI is recorded in
the module as provenance, deliberately not as a constant — hardcoding this one
would reproduce the same bug the next time the endpoint moves.

The related fix is in the error path. A document that genuinely contains no
`sdnEntry` elements now fails with the namespace it declared and the child
elements it does contain, because "zero entries" on its own sends the reader
looking for an OFAC outage when the cause is a schema change.

## 2. Two corpora sharing a key space but not a universe

The demo and the live run wrote to the same snapshot store. So a live run found
yesterday's *synthetic* fixture snapshot, treated it as the previous
publication, and reported every real EU designation as new and every invented
company as delisted.

This is the same false-quiet-day failure the package exists to prevent, run in
reverse: a false *loud* day. Fixed by splitting the store —
`data/snapshots/fixture/` and `data/snapshots/live/` — with a regression test
that runs the demo and then a live run and asserts the second is a baseline.

The general rule the bug taught: two datasets that share a key space but not a
universe must never be diffed, and nothing in the key format itself will tell
you when that is happening.

## 3. The payload you discard is the one you needed

Raw payloads were archived *after* parsing. So when OFAC failed to parse, the
28.8 MB file that would have shown the namespace change was thrown away, and
the publisher had already overwritten it.

Archiving now happens before parsing, and the failure message says where the
payload was kept. A monitor that only retains data it could understand cannot
diagnose the days it did not.

## 4. The obvious key is the wrong key

The trade.gov bulk file has no `entity_number`. Its only per-record identifier
is a 56-hex-character digest that trade.gov generates. If that digest is
derived from record content — its shape suggests it is — then adding a single
alias changes it, and a differ keyed on it reports a routine amendment as a
delisting plus a new designation.

Delistings are the delta a customer acts on immediately, so manufacturing false
ones is worse than missing real amendments.

The key is now composed from the fields that identify the *party* rather than
describe it: list, normalised name, listing date. Those survive the edits that
happen on ordinary publication days. They do not survive a name correction,
which surfaces as a removal plus an addition — rarer, and worth an analyst's
attention anyway. `key_stability` is declared as `composed` so the
reconciliation check says which of the two reasons a removal needs review.

The publisher's digest is carried through as an identifier rather than
discarded. If it is content-derived, that shows up as identifier churn on
otherwise unchanged records — turning a suspicion into evidence.

## 5. A flattering number that was false

A consequence of (4), caught while reading the first clean run. Carrying the
digest as an identifier made every BIS record "have an identifier", so the
inspect summary reported **100% joinable to a corporate register** for a source
that publishes no registry numbers at all.

The statistic now counts only identifiers that could actually join to a
register, and reports provenance-only records separately. A metric that
improves because of a bookkeeping change, on data that did not improve, is
worse than no metric.

## What the fixtures could and could not catch

The committed corpus reproduces the wire formats faithfully enough that all
four parsers were correct on structure. What it could not reproduce was the
gap between what a publisher documents and what it serves — which is where
every one of these bugs lived.

The corollary is not "fixtures are useless". It is that fixtures test the
parser against your understanding of the format, and live data tests your
understanding.
