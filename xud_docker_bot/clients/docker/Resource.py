from dataclasses import dataclass
from typing import Dict


@dataclass
class Resource:
    digest: str
    payload: Dict
