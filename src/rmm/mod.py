import xml.etree.ElementTree as ET
from multiprocessing import Pool
from pathlib import Path
from typing import Optional
from rmm import xml_parser

from . import util


class Mod:
    def __init__(
        self,
        id: str,
        name: str,
        author: str,
        repository_url: Optional[str] = None,
        steam_id: Optional[int] = None,
    ) -> None:
        self.id = id.lower()
        self.name = name
        self.author = author
        self.repository_url = repository_url
        self.steam_id = steam_id

    @property
    def title(self) -> str:
        return self.id or f"{self.name} by {self.author}"

    @classmethod
    def create_from_path(cls, path: Path) -> "Mod":
        """Create a Mod object from the given path."""
        try:
            about_xml_path = xml_parser.find_about_xml(path)
        except NoAboutXMLFile:
            raise

        tree_root = xml_parser.parse_tree(about_xml_path)

        try:
            package_id = xml_parser.extract_packageid(tree_root)
        except NoPackageId:
            raise NoPackageId(path)

        author = util.element_grab("author", tree_root) or "Unknown"
        name = util.element_grab("name", tree_root) or "Unknown"

        return cls(
            id=package_id,
            name=name,
            author=author,
            steam_id=xml_parser.read_steamid(path),
        )

    def __str__(self) -> str:
        return self.id


class NoPackageId(Exception):
    pass


class NoAboutXMLFile(Exception):
    pass


class ModFolder:
    def read(self, path: Path) -> list[Mod]:
        with Pool(16) as pool:
            mods = list(filter(None, pool.map(Mod.create_from_path, path.iterdir())))
        return mods

    def read_dict(self, path: Path) -> dict[str, Mod]:
        mods = self.read(path)
        return {mod.id: mod for mod in mods if mod.id}

    def search(self, path: Path, search_term: str) -> list[Mod]:
        return [
            mod
            for mod in self.read(path)
            if mod.name
            and search_term.lower() in mod.name.lower()
            or mod.author
            and search_term.lower() in mod.author.lower()
            or mod.steam_id
            and search_term == str(mod.steam_id)
        ]

    def search_dict(self, path: Path, search_term: str) -> dict[str, Mod]:
        mods = self.search(path, search_term)
        return {mod.id: mod for mod in mods if mod.id}
