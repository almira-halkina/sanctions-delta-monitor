"""Source adapters.

Each adapter takes bytes as published by the regulator and returns a
`Snapshot`. Nothing in here touches the network: fetching is separated from
parsing (`regdelta.fetch`) so that the parsers can be tested against committed
fixtures in the exact wire format, and so a bad publication day can be replayed
from the snapshot store rather than re-downloaded.
"""

from regdelta.sources.base import ParseError, SourceAdapter
from regdelta.sources.bis_csl import BisCslAdapter
from regdelta.sources.eu_fsd import EuFsdAdapter
from regdelta.sources.federal_register import FederalRegisterAdapter
from regdelta.sources.ofac_sdn import OfacSdnAdapter

ADAPTERS: dict[str, SourceAdapter] = {
    "ofac_sdn": OfacSdnAdapter(),
    "bis_csl": BisCslAdapter(),
    "eu_fsd": EuFsdAdapter(),
}

__all__ = [
    "ADAPTERS",
    "BisCslAdapter",
    "EuFsdAdapter",
    "FederalRegisterAdapter",
    "OfacSdnAdapter",
    "ParseError",
    "SourceAdapter",
]
