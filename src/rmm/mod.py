#!/usr/bin/env python3

from __future__ import annotations

import xml.etree.ElementTree as ET
from multiprocessing import Pool
from pathlib import Path
from typing import Optional, cast
from dataclasses import dataclass
from collections import OrderedDict

import rmm.util as util
from rmm.exception import InvalidPackageHash
DEBUG = False


@dataclass
class Mod:
    def __init__(
        self,
        packageid: Optional[str] = None,
        before: Optional[list[str]] = None,
        after: Optional[list[str]] = None,
        incompatible: Optional[list[str]] = None,
        dirname: Optional[Path] = None,
        author: Optional[str] = None,
        name: Optional[str] = None,
        versions: Optional[list[str]] = None,
        steamid: Optional[int] = None,
        ignored: bool = False,
        repo_url: Optional[str] = None,
        workshop_managed: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ):
        if packageid and isinstance(packageid, str):
            self.packageid = packageid.lower()
        else:
            self.packageid = packageid
        self.before = Mod.lowercase_set(before)
        self.after = Mod.lowercase_set(after)
        self.incompatible = incompatible
        self.dirname = dirname
        self.author = author
        self.name = name
        self.ignored = ignored
        self.steamid = steamid
        self.versions = versions
        self.repo_url = repo_url
        self.workshop_managed = workshop_managed
        self.enabled = enabled

    def title(self):
        return self.packageid if self.packageid else f"{self.name} by {self.author}"

    @staticmethod
    def lowercase_set(data):
        retval = set()
        try:
            for n in data:
                try:
                    retval.add(n.lower())
                except AttributeError:
                    continue
        except TypeError:
            return None
        return retval

    @staticmethod
    def create_from_workshorp_result(wr: WorkshopResult):
        return Mod(steamid=wr.steamid, name=wr.name, author=wr.author)

    @staticmethod
    def create_from_path(path) -> Optional[Mod]:
        try:
            tree = ET.parse(path / "About/About.xml")
            root = tree.getroot()
            try:
                packageid = cast(str, cast(ET.Element, root.find("packageId")).text)
            except AttributeError as e:
                name = util.element_grab("name", root)
                author = util.element_grab("author", root)
                if name and author:
                    packageid = "{}.{}".format(name.lower(), author.lower())
                else:
                    if DEBUG:
                        raise e
                    return None

            def read_steamid(path: Path) -> Optional[int]:
                try:
                    return int(
                        (path / "About" / "PublishedFileId.txt")
                        .read_text()
                        .strip()
                        .encode("ascii", errors="ignore")
                        .decode()
                    )
                except (OSError, ValueError, IOError) as e:
                    if DEBUG:
                        print(e)
                    return None

            def read_ignored(path: Path):
                try:
                    return (path / ".rmm_ignore").is_file()
                except (OSError) as e:
                    print(e)
                    return False

            return Mod(
                packageid=packageid,
                before=util.list_grab("loadAfter", root),
                after=util.list_grab("loadBefore", root),
                incompatible=util.list_grab("incompatibleWith", root),
                dirname=path.name,
                author=util.element_grab("author", root),
                name=util.element_grab("name", root),
                versions=util.list_grab("supportedVersions", root),
                steamid=read_steamid(path),
                ignored=read_ignored(path),
            )

        except OSError as e:
            # if not "Place mods here" in path.name:
            print(f"Ignoring {path}")
            # raise e

    def __eq__(self, other):
        if isinstance(other, Mod):
            if self.packageid and other.packageid:
                return self.packageid == other.packageid
            if self.steamid and other.steamid:
                return self.steamid == other.steamid
        if isinstance(other, str) and self.packageid:
            return self.packageid.lower() == other.lower()
        if isinstance(other, int) and self.steamid:
            return self.steamid == other
        return NotImplemented

    def __hash__(self):
        if not self.packageid:
            raise InvalidPackageHash()
        return hash(self.packageid)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"<Mod: '{self.packageid}'>"

    @staticmethod
    def list_to_dict(mods: list[Mod]):
        hm = dict()
        for n in mods:
            if not n.packageid:
                raise Exception("No package id in hashmap")
            hm[n.packageid] = n

        return hm


class ModFolder:
    @staticmethod
    def read(path: Path) -> list[Mod]:
        with Pool(16) as p:
            mods = cast(
                list[Mod],
                list(
                    filter(
                        None,
                        p.map(
                            Mod.create_from_path,
                            path.iterdir(),
                        ),
                    )
                ),
            )

        return mods

    @staticmethod
    def read_dict(path: Path):
        return Mod.list_to_dict(ModFolder.read(path))

    @staticmethod
    def search(path: Path, search_term) -> list[Mod]:
        return [
            r
            for r in ModFolder.read(path)
            if (isinstance(r.name, str) and search_term.lower() in r.name.lower())
            or (isinstance(r.author, str) and search_term.lower() in r.author.lower())
            or search_term == r.steamid
        ]

    @staticmethod
    def search_dict(path: Path, search_term) -> dict[str, Mod]:
        return Mod.list_to_dict(ModFolder.search(path, search_term))


EXPANSION_PACKAGES = [
    Mod(packageid="ludeon.rimworld", author="Ludeon", name="RimWorld"),
    Mod(packageid="ludeon.rimworld.ideology", author="Ludeon", name="Ideology"),
    Mod(packageid="ludeon.rimworld.royalty", author="Ludeon", name="Royalty"),
]
