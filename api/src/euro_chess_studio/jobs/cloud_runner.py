import sqlite3

from euro_chess_studio.jobs.base import JobConfig, JobOutput


class CloudRunner:
    """Stub for v0. No cloud execution exists yet; this only documents the
    interface a future remote runner would implement.
    """

    def run(self, conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
        raise NotImplementedError("CloudRunner is not implemented in v0")
