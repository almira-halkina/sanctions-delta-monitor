"""Paths and run configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    fixtures: Path
    snapshots: Path
    output: Path

    @classmethod
    def default(cls) -> Paths:
        root = Path(os.environ.get("REGDELTA_ROOT", REPO_ROOT))
        return cls(
            fixtures=root / "fixtures",
            snapshots=root / "data" / "snapshots",
            output=root / "output",
        )

    def ensure(self) -> None:
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)


#: The date the BIS Affiliates Rule suspension lapses and the rule is
#: reimposed, absent further Commerce action. Tracked as a constant because
#: the whole watch module exists to answer whether it is still true.
AFFILIATES_RULE_REIMPOSITION = "2026-11-10"
