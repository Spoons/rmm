#!/bin/python3
"""
RimWorld Mod Manager

Usage:
  rmm backup <file>
  rmm export [options] <file>
  rmm import [options] <file>
  rmm list [options]
  rmm migrate [options]
  rmm query [options] [<term>...]
  rmm remove [options] [<term>...]
  rmm search <term>...
  rmm sync [options] [sync options] <name>...
  rmm update [options] [sync options]
  rmm -h | --help
  rmm -v | --version

Operations:
  backup            Backups your mod directory to a tar, gzip,
                      bz2, or xz archive. Type inferred by name.
  export            Save mod list to file.
  import            Install a mod list from a file.
  list              List installed mods.
  migrate           Remove mods from workshop and install locally.
  query             Search installed mods.
  remove            Remove installed mod.
  search            Search Workshop.
  sync              Install or update a mod.
  update            Update all mods from Steam.

Parameters
  term              Name, author, steamid
  file              File path
  name              Name of mod.

Sync Options:
  -f --force        Force mod directory overwrite

Options:
  -p --path DIR     RimWorld path.
  -w --workshop DIR Workshop Path.
"""

from __future__ import annotations
from typing import Iterable, cast, Optional, Type, Generator
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path
import docopt
import urllib.request
from multiprocessing import Pool
import networkx as nx
import matplotlib.pyplot as plt
from enum import Enum

from bs4 import BeautifulSoup


class Mod:
    def __init__(
        self,
        packageid: str,
        before: Optional[list[str]] = None,
        after: Optional[list[str]] = None,
        incompatible: Optional[list[str]] = None,
        path: Optional[Path] = None,
        author: Optional[str] = None,
        name: Optional[str] = None,
        versions: Optional[list[str]] = None,
        steamid: Optional[int] = None,
        ignored: bool = False,
        repo_url: Optional[str] = None,
    ):
        self.packageid = packageid
        self.before = before
        self.after = after
        self.incompatible = incompatible
        self.path = path
        self.author = author
        self.name = name
        self.ignored = ignored
        self.steamid = steamid
        self.versions = versions
        self.repo_url = repo_url

    @staticmethod
    def create_from_path(dirpath) -> Optional[Mod]:
        try:
            tree = ET.parse(dirpath / "About/About.xml")
            root = tree.getroot()

            try:
                packageid = cast(str, cast(ET.Element, root.find("packageId")).text)
            except AttributeError:
                return None

            def xml_list_grab(element: str) -> Optional[list[str]]:
                try:
                    return cast(
                        Optional[list[str]],
                        [
                            n.text
                            for n in cast(ET.Element, root.find(element)).findall("li")
                        ],
                    )
                except AttributeError:
                    return None

            def xml_element_grab(element: str) -> Optional[str]:
                try:
                    return cast(ET.Element, root.find(element)).text
                except AttributeError:
                    return None

            def read_steamid(path: Path) -> Optional[int]:
                try:
                    return int((path / "About" / "PublishedFileId.txt").read_text())
                except (OSError, ValueError):
                    return None

            def read_ignored(path: Path):
                try:
                    return (path / ".rmm_ignore").is_file()
                except (OSError):
                    return False

            return Mod(
                packageid,
                before=xml_list_grab("loadAfter"),
                after=xml_list_grab("loadBefore"),
                incompatible=xml_list_grab("incompatibleWith"),
                path=dirpath,
                author=xml_element_grab("author"),
                name=xml_element_grab("name"),
                versions=xml_list_grab("supportedVersions"),
                steamid=read_steamid(dirpath),
                ignored=read_ignored(dirpath),
            )

        except OSError as e:
            print(f"Could not read {dirpath}")
            return None

    def __eq__(self, other):
        if isinstance(other, Mod):
            return self.packageid == other.packageid
        if isinstance(other, str):
            return self.packageid == other
        return NotImplemented

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"pid: {self.packageid}"


class ModFolderReader:
    @staticmethod
    def create_mods_list(path) -> list[Mod]:
        with Pool(16) as p:
            mods = filter(
                None,
                p.map(
                    Mod.create_from_path,
                    path.iterdir(),
                ),
            )
        return list(mods)


class ModListFileFormat:
    MAGIC_ID = "rmm_modlist_v2"
    SEPERATOR = "::"
    PACKAGE_ID = 0
    STEAM_ID = 1
    REPO_URL = 2

    @classmethod
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        for line in text:
            parsed = line.split(str(cls.SEPERATOR))
            try:
                if not parsed[cls.PACKAGE_ID]:
                    continue
                yield Mod(
                    parsed[cls.PACKAGE_ID],
                    steamid=int(parsed[cls.STEAM_ID]),
                    repo_url=parsed[cls.REPO_URL] if not "" else None,
                )
            except ValueError:
                continue

    @classmethod
    def format(cls, mod: Mod):
        return cls.SEPERATOR.join(
            [
                mod.packageid,
                str(mod.steamid) if not None else "",
                mod.repo_url if not None else "",
            ]
        )


class ModListReader:
    @staticmethod
    def read(path: Path) -> Optional[list[Mod]]:
        try:
            with path as f:
                text = f.read_text()
        except OSError:
            return None

        return [m for m in ModListFileFormat.parse(text)]

    @staticmethod
    def read_v1(path: Path) -> Optional[list[Mod]]:
        pass

    @staticmethod
    def write(path: Path, mods: list[Mod]):
        try:
            with path as f:
                [path.write_text(ModListFileFormat.format(m)) for m in mods]
        except OSError:
            return False
        return True

class SteamDownloader:
    @staticmethod
    def download(mods: List[Mod], folder: Path):
        def workshop_format(mods):
            return (s := " +workshop_download_item 294100 ") + s.join(
                m.steamid for m in mods if not None
            )

        query = 'env HOME="{}" steamcmd +login anonymous "{}" +quit >&2'.format(
            str(folder), workshop_format(mods)
        )
        run_sh(query)


if __name__ == "__main__":
    mods = ModFolderReader.create_mods_list(
        Path("/tmp/rmm/.steam/steamapps/workshop/content/294100/")
    )
    DG = nx.DiGraph()

    ignore = ["brrainz.harmony", "UnlimitedHugs.HugsLib"]
    for m in mods:
        if m.after:
            for a in m.after:
                if a in mods:
                    if not a in ignore and not m.packageid in ignore:
                        DG.add_edge(a, m.packageid)
        if m.before:
            for b in m.before:
                if b in mods:
                    if not b in ignore and not m.packageid in ignore:
                        DG.add_edge(m.packageid, b)

    pos = nx.spring_layout(DG, seed=56327, k=0.8, iterations=15)
    nx.draw(
        DG, pos, node_size=100, alpha=0.8, edge_color="r", font_size=8, with_labels=True
    )
    ax = plt.gca()
    ax.margins(0.08)

    print("topological sort:")
    sorted = list(nx.topological_sort(DG))
    for n in sorted:
        print(n)

    plt.show()
