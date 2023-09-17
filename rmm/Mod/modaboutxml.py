#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional, Union, cast


@dataclass
class ModDep:
    package_id: str
    name: str
    workshop_url: str
    download_url: str


def __eq__(self, other) -> bool:
    return self.package_id == other.package_id


@dataclass
class ModAboutXML:
    package_id: str
    before: List[str]
    after: Optional[List[str]]
    incompatible: Optional[List[str]]
    author: Optional[str]
    name: Optional[str]
    supported_versions: List[str]
    dependencies: Optional[List[ModDep]]

    def display_name(self) -> str:
        return self.name or self.package_id or f"{self.author}"

    #
    def __eq__(self, other) -> bool:
        return self.package_id == other.package_id

    def __hash__(self) -> int:
        return hash(self.package_id)
