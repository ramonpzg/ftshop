"""Job runner abstraction. The UI never knows which runner handles a job
type -- that mapping lives entirely in jobs/registry.py.
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class JobConfig:
    job_type: str
    params: dict
    workspace_id: str | None = field(default=None)


@dataclass(frozen=True)
class JobOutput:
    modality: str
    kind: str
    payload: dict
    # True when the output came from a cached fixture rather than a live
    # calculation. Carried on the output so callers never need to know
    # which runner produced it.
    cached: bool = field(default=False)


class JobRunner(Protocol):
    def run(self, conn: sqlite3.Connection, job: JobConfig) -> JobOutput: ...
