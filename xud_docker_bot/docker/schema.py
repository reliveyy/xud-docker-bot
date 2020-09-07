#from __future__ import annotations
# marshmallow cannot work with "annotations" which changes date type into str

from dataclasses import dataclass
from typing import Optional, List, TypeVar, Generic
import marshmallow_dataclass


@dataclass
class Image:
    architecture: str
    features: str
    variant: Optional[str]
    digest: str
    os: str
    os_features: str
    os_version: Optional[str]
    size: int


@dataclass
class Manifest:
    creator: int
    id: int
    image_id: Optional[int]
    images: List[Image]
    last_updated: str
    last_updater: int
    last_updater_username: str
    name: str
    repository: int
    full_size: int
    v2: bool


T = TypeVar('T')


@dataclass
class Page(Generic[T]):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[T]


@dataclass
class Tag:
    name: str
    size: int


# class ManifestPage(Page[Manifest]):
#     pass

@dataclass
class ManifestPage:
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[Manifest]


@dataclass
class Repository:
    user: str
    name: str
    namespace: str
    repository_type: str
    status: int
    description: str
    is_private: bool
    is_automated: bool
    can_edit: bool
    star_count: int
    pull_count: int
    last_updated: str
    is_migrated: bool


@dataclass
class RepositoryPage:
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[Repository]


ManifestPageSchema = marshmallow_dataclass.class_schema(ManifestPage)
RepositoryPageSchema = marshmallow_dataclass.class_schema(RepositoryPage)
