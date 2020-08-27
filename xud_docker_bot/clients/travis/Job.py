from dataclasses import dataclass


@dataclass
class Job:
    job_id: int
    build_id: int
    state: str
    log: str
