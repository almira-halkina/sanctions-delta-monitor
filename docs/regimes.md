# The three regimes

The whole point of this repository is that "restricted" is not a property of a
list. It is the output of a rule applied to a list *and* an ownership graph,
and there are three such rules in force over the same corporate structures.
They do not agree.

Each is encoded as data in `src/regdelta/ownership/closure.py`, so the same
graph can be run through all three and the divergences reported. Nothing about
the traversal changes between them; only the parameters do.

| | OFAC 50 Percent Rule | BIS Affiliates Rule | EU ownership or control |
|---|---|---|---|
| Threshold | 50% **or more** | 50% **or more** | **more than** 50% |
| Aggregation | across all blocked persons | across Entity List, MEU **and** SDN | across all designated persons |
| Indirect | yes, by closure | yes, by closure | yes, by closure |
| Non-percentage control test | no | no | **yes** |
| Consequence | property blocked | licence requirement attaches | funds frozen / no funds made available |
| Affiliates published? | no | **no, explicitly** | no |
| Status | in force | suspended to 9 Nov 2026, reimposed 10 Nov 2026 | in force |

## OFAC — the 50 Percent Rule

*Revised Guidance on Entities Owned by Persons Whose Property and Interests in
Property Are Blocked, 13 August 2014.*

> Any entity owned in the aggregate, directly or indirectly, 50 percent or more
> by one or more blocked persons is itself considered to be a blocked person.

Two words carry most of the weight.

**"Aggregate."** Stakes held by different blocked persons sum. Two unrelated
SDNs holding 25% each produce a blocked entity, even though neither could block
it alone.

**"Indirectly."** This is where implementations go wrong, and the error is
always in the same direction. The intuitive reading multiplies along the chain:
a blocked person owns 60% of A, A owns 60% of B, so the blocked person's
effective interest in B is 36% and B is clean. That is not the rule. Once A is
blocked by operation of the rule, A *is* a blocked person, and A's 60% of B is
a blocked person's 60% holding. B is blocked.

So propagation is a fixed point, not a product:

```
restricted = {seeds}
repeat until no change:
    for each entity not yet restricted:
        if sum(stake for each restricted owner) >= 50: mark restricted
```

The iteration is also what makes the computation safe on circular
shareholdings, which are common in exactly the structures worth investigating.
`test_indirect_ownership_is_not_multiplicative` and
`test_circular_shareholding_terminates` pin both properties.

What the rule does **not** do: attribute through a non-blocked intermediate. A
blocked person holding 40% of A, where A holds 100% of B, does not block
B — A never becomes blocked, so nothing propagates.

## BIS — the Affiliates Rule

*90 FR 47254, 29 September 2025. Suspended by 90 FR 52099, 12 November 2025,
for one year. Reimposed 10 November 2026 and continuing indefinitely, absent
further Commerce action.*

Same threshold and same aggregation as OFAC, with three differences that
matter operationally.

**The seed set is wider.** Ownership by Entity List parties, MEU List parties
and SDNs aggregates *together*. A joint venture 30% held by an SDN and 20% held
by an Entity List party reaches 50% under this rule and under no other. That
case is in the fixture corpus as Meridian General Trading FZE, and in the tests
as `test_bis_aggregates_entity_list_and_sdn_holdings_together`.

**The consequence is a licence requirement, not a block.** The affiliate
inherits the licence requirement and licence review policy of its listed
parent, which is why `Record.license_requirement` is carried through the
schema.

**Affiliates are not listed.** BIS said so in the preamble: affiliates caught by
the rule will not be added to the Entity List. So from 10 November 2026 the
Consolidated Screening List remains a complete record of *listed* parties and
becomes an incomplete record of *restricted* parties. Screening against the CSL
alone is under-inclusive by construction, and the size of the gap is not
published by anyone.

The suspension was traded for China's suspension of its October 2025 rare-earth
export controls. That makes the reimposition date contingent on a bilateral
arrangement rather than on a regulatory calendar, which is why
`src/regdelta/watch.py` monitors the docket rather than trusting the date.

## EU — ownership or control

*Council Best Practices for the effective implementation of restrictive
measures, 8519/18, paragraphs 62-63.*

Two tests, either sufficient.

**Ownership** is a holding of *more than* 50%. Not "or more". An entity held at
exactly 50.0% by a designated person is restricted in the United States and not
restricted in the European Union. One word of legal text, two different answers
about the same company — `test_exactly_fifty_percent_splits_us_from_eu`.

**Control** is qualitative and has no threshold at all: the right to appoint or
remove a majority of the board, the ability to direct policy, a dominant
influence under a contract or the articles. A 30% stake with the right to
appoint directors satisfies it. No percentage-based implementation can find
these, which is why `OwnershipEdge.control_indicators` exists as a separate
field and why the EU regime is the only one with `control_test=True`.

## Unknown is not zero

Registers routinely omit percentages. UK PSC filings report bands rather than
numbers; several jurisdictions report nothing.

An entity whose *known* restricted-owner aggregate is below the threshold, but
which has restricted owners holding an unrecorded stake, is returned as
`INDETERMINATE`. It is a research queue, not a verdict. Collapsing that state
into "clear" is how a wholly-owned subsidiary of a designated parent passes
screening, and it is the most consequential silent failure available in this
problem.

Where a band is available, it is read at its floor. "25% to 50%" is taken as
25%, so it does not on its own trip a 50% threshold. Reading the midpoint would
invent a restriction the filing cannot evidence.

## What is deliberately not modelled

- **OFAC's control-without-ownership position.** OFAC warns that entities
  controlled but not 50%-owned by blocked persons carry risk, but does not
  block them by rule. Encoding that as a restriction would overstate what the
  guidance says.
- **Sectoral programmes (Directives 1-4).** These impose transaction-type
  restrictions, not blocking, and their propagation rules differ per directive.
  A re-designation from a sectoral to a blocking programme is detected and
  classified, but sectoral consequences are not derived.
- **De minimis and EAR item scope.** Whether a specific shipment needs a
  licence depends on the item's classification, not only on the counterparty.
  This computes the counterparty side.
