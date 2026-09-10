from __future__ import annotations

from abc import ABC, abstractmethod

from regdelta.schema import Snapshot, SourceId


class ParseError(RuntimeError):
    """Raised when a publication cannot be parsed.

    Deliberately fatal rather than best-effort. A partially parsed sanctions
    list produces false 'removed' verdicts for every entry the parser dropped,
    which in a screening context is the expensive direction to be wrong in.
    """


class SourceAdapter(ABC):
    source: SourceId
    #: Whether the publisher's primary key survives across publications.
    #: "stable"    - key is durable; a missing key means genuine delisting.
    #: "unstable"  - key may be reassigned; 'removed' verdicts need review.
    key_stability: str = "stable"
    #: Human-readable pointer to where the bytes come from.
    endpoint: str = ""

    @abstractmethod
    def parse(self, payload: bytes, as_of: str) -> Snapshot: ...
