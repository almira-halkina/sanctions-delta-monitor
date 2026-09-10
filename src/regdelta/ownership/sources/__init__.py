"""Real ownership sources.

Two free, public datasets, chosen because between them they cover the two
things the closure needs and neither provides alone.

**UK Companies House PSC** publishes beneficial ownership with percentage
*bands*, so it can actually trip a 50% threshold. It is one jurisdiction.

**GLEIF Level 2** publishes direct and ultimate accounting-consolidating
parents for legal entities worldwide, with no percentages at all. It is global
and says nothing about how much of a company someone owns.

That asymmetry is not a defect of the sources, it is the shape of the problem.
Percentage data is national and patchy; global data is structural. Running both
through the same closure is what makes the divergence between the US and EU
tests visible on real companies rather than invented ones: a
consolidating-parent edge is an unrecorded stake to OFAC and BIS, and evidence
of control to the EU.
"""

from regdelta.ownership.sources.base import IngestResult, OwnershipSource
from regdelta.ownership.sources.companies_house import CompaniesHousePsc
from regdelta.ownership.sources.gleif import GleifLevel2

__all__ = ["CompaniesHousePsc", "GleifLevel2", "IngestResult", "OwnershipSource"]
