from dataclasses import dataclass
from datetime import datetime


@dataclass
class DockerImage:
    digest: str
    revision: str
    app_revision: str
    created_at: datetime
