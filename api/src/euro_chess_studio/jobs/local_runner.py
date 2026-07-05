import sqlite3

from euro_chess_studio.jobs.base import JobConfig, JobOutput
from euro_chess_studio.jobs.local_handlers import LOCAL_HANDLERS


class UnknownJobTypeError(ValueError):
    pass


class LocalRunner:
    """Runs a tiny real calculation over the app's own data."""

    def run(self, conn: sqlite3.Connection, job: JobConfig) -> JobOutput:
        handler = LOCAL_HANDLERS.get(job.job_type)
        if handler is None:
            raise UnknownJobTypeError(f"no local handler for job type: {job.job_type}")
        return handler(conn, job)
