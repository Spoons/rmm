#!/bin/python3
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Generator, Iterable, Iterator, Optional, cast
from xml.dom import minidom

from bs4 import BeautifulSoup


class Useage:
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


class Util:
    @staticmethod
    def platform() -> Optional[str]:
        unixes = ["darwin", "linux", "freebsd"]
        windows = "win32"

        for n in unixes:
            if sys.platform.startswith(n):
                return "unix"
        if sys.platform.startswith("win32"):
            return "win32"

        return None

    @staticmethod
    def execute(cmd) -> Generator[str, None, None]:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            text=True,
            close_fds=True,
            shell=True,
        ) as proc:
            for line in iter(proc.stdout.readline, b""):
                yield line
                if (r := proc.poll()) is not None:
                    if r != 0:
                        raise subprocess.CalledProcessError(r, cmd)
                    break

    @staticmethod
    def run_sh(cmd: str) -> str:
        return subprocess.check_output(cmd, text=True, shell=True).strip()

    @staticmethod
    def copy(source: Path, destination: Path, recursive: bool = False):
        if recursive:
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination, follow_symlinks=True)

    @staticmethod
    def move(source: Path, destination: Path):
        shutil.move(source, destination)

    @staticmethod
    def remove(dest: Path):
        shutil.rmtree(dest)


class XMLUtil:
    @staticmethod
    def list_grab(element: str, root: ET.ElementTree) -> Optional[list[str]]:
        try:
            return cast(
                Optional[list[str]],
                [n.text for n in cast(ET.Element, root.find(element)).findall("li")],
            )
        except AttributeError:
            return None

    @staticmethod
    def element_grab(element: str, root: ET.ElementTree) -> Optional[str]:
        try:
            return cast(ET.Element, root.find(element)).text
        except AttributeError:
            return None


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
        workshop_managed: Optional[bool] = None,
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
        self.workshop_managed = workshop_managed

    @staticmethod
    def create_from_path(dirpath) -> Optional[Mod]:
        try:
            tree = ET.parse(dirpath / "About/About.xml")
            root = tree.getroot()

            try:
                packageid = cast(str, cast(ET.Element, root.find("packageId")).text)
            except AttributeError:
                return None

            def read_steamid(path: Path) -> Optional[int]:
                try:
                    return int((path / "About" / "PublishedFileId.txt").read_text())
                except (OSError, ValueError) as e:
                    print(e)
                    return None

            def read_ignored(path: Path):
                try:
                    return (path / ".rmm_ignore").is_file()
                except (OSError) as e:
                    print(e)
                    return False

            return Mod(
                packageid,
                before=XMLUtil.list_grab("loadAfter", root),
                after=XMLUtil.list_grab("loadBefore", root),
                incompatible=XMLUtil.list_grab("incompatibleWith", root),
                path=dirpath,
                author=XMLUtil.element_grab("author", root),
                name=XMLUtil.element_grab("name", root),
                versions=XMLUtil.list_grab("supportedVersions", root),
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
        return f"<Mod: '{self.packageid}'>"


class ModStub(Mod):
    def __init__(self, steamid):
        super().__init__("", steamid=steamid)

    def __str__(self):
        return f"<ModStub: '{self.steamid}'>"


class ModList(MutableSequence):
    def __init__(self, data: Iterable[Mod], name: Optional[str] = None):
        if not isinstance(data, MutableSequence):
            self.data = list(data)
        else:
            self.data = data
        self.name = name

    def __getitem__(self, key: int) -> Mod:
        return self.data[key]

    def __setitem__(self, key: int, value: Mod) -> None:
        self.data[key] = value

    def __delitem__(self, key: int) -> None:
        del self.data[key]

    def __len__(self) -> int:
        return len(self.data)

    def insert(self, i, x):
        self.data[i] = x

    def __repr__(self):
        return f"<ModList: {self.data.__repr__()}>"


class ModFolderReader:
    @staticmethod
    def create_mods_list(path) -> ModList[Mod]:
        with Pool(16) as p:
            mods = filter(
                None,
                p.map(
                    Mod.create_from_path,
                    path.iterdir(),
                ),
            )
        return ModList(mods)


class ModListSerializer(ABC):
    @classmethod
    @abstractmethod
    def parse(cls, text: str) -> None:
        pass

    @classmethod
    @abstractmethod
    def serialize(cls, mods: MutableSequence) -> None:
        pass


class CsvStringBuilder:
    def __init__(self):
        self.value = []

    def write(self, row: str) -> None:
        self.value.append(row)

    def pop(self) -> None:
        return self.value.pop()

    def __iter__(self) -> Iterator[str]:
        return iter(self.value)


class ModListV2Format(ModListSerializer):
    HEADER = {"PACKAGE_ID": 0, "STEAM_ID": 1, "REPO_URL": 2}
    MAGIC_FLAG = "RMM_V2_MODLIST"

    @classmethod
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        reader = csv.reader(text.split("\n"))
        for parsed in reader:
            try:
                yield Mod(
                    parsed[cls.HEADER["PACKAGE_ID"]],
                    steamid=int(parsed[cls.HEADER["STEAM_ID"]]),
                    repo_url=parsed[cls.HEADER["REPO_URL"]] if not "" else None,
                )
            except (ValueError, IndexError):
                print("Unable to import: ", parsed)
                continue

    @classmethod
    def serialize(cls, mods: MutableSequence) -> Generator[str, None, None]:
        buffer = CsvStringBuilder()
        writer = csv.writer(cast(Any, buffer))
        for m in mods:
            writer.writerow(cls.format(m))
            yield buffer.pop().strip()

    @classmethod
    def format(cls, mod: Mod) -> list[str]:
        return cast(
            list[str],
            [
                mod.packageid,
                str(mod.steamid) if not None else "",
                mod.repo_url if not None else "",
            ],
        )


class ModListV1Format(ModListSerializer):
    STEAM_ID = 0

    @classmethod
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        for line in text.split("\n"):
            parsed = line.split("#", 1)
            try:
                yield ModStub(
                    int(parsed[cls.STEAM_ID]),
                )
            except ValueError:
                if line:
                    print("Unable to import: ", line)
                continue

    @classmethod
    def serialize(cls, mods: MutableSequence) -> Generator[str, None, None]:
        for m in mods:
            yield cls.format(m)

    @classmethod
    def format(cls, mod: Mod) -> str:
        return "{}# {} by {} ".format(str(mod.steamid), mod.name, mod.author)


class ModListStreamer:
    @staticmethod
    def read(path: Path, serializer: ModListSerializer) -> Optional[MutableSequence]:
        try:
            with path.open("r") as f:
                text = f.read()
        except OSError as e:
            print(e)
            return None

        return [m for m in serializer.parse(text)]

    @staticmethod
    def write(path: Path, mods: MutableSequence, serializer: ModListSerializer):
        try:
            with path.open("w+") as f:
                [f.write(line + "\n") for line in serializer.serialize(mods)]
        except OSError as e:
            print(e)
            return False
        return True


class SteamDownloader:
    def __init__(self, folder: Path):
        self.home_path = folder
        self.mod_path = folder / ".steam/steamapps/workshop/content/294100/"

    def _get(self, mods: MutableSequence):
        def workshop_format(mods):
            return (s := " +workshop_download_item 294100 ") + s.join(
                m.steamid for m in mods if not None
            )

        query = 'env HOME="{}" steamcmd +login anonymous "{}" +quit >&2'.format(
            str(self.home_path), workshop_format(mods)
        )
        return Util.run_sh(query)

    def download(self, mods: MutableSequence[Mod]) -> ModList:
        self._get(mods)
        return ModFolderReader.create_mods_list(self.home_path)


class WorkshopResult:
    def __init__(
        self,
        steamid,
        name=None,
        author=None,
        description=None,
        update_time=None,
        size=None,
        num_rating=None,
        rating=None,
        create_time=None,
        num_ratings=None,
    ):
        self.steamid = steamid
        self.name = name
        self.author = author
        self.description = description
        self.update_time = update_time
        self.size = size
        self.create_time = create_time
        self.num_ratings = num_ratings
        self.rating = rating

    def __str__(self):
        return "\n".join(
            [
                prop + ": " + str(getattr(self, prop))
                for prop in self.__dict__
                if not callable(self.__dict__[prop])
            ]
        )

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other: WorkshopResult) -> bool:
        if not isinstance(other, WorkshopResult):
            raise NotImplementedError
        return self.steamid == other.steamid

    def _merge(self, other: WorkshopResult):
        if not isinstance(other, WorkshopResult):
            raise NotImplementedError
        for prop in other.__dict__:
            if (
                not callable(other.__dict__[prop])
                and hasattr(self, prop)
                and getattr(other, prop)
            ):
                setattr(self, prop, (getattr(other, prop)))

    def get_details(self):
        self._merge(WorkshopWebScraper.detail(self.steamid))
        return self


class WorkshopWebScraper:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    }
    index_query = (
        "https://steamcommunity.com/workshop/browse/?appid=294100&searchtext={}"
    )
    detail_query = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"

    @classmethod
    def _request(cls, url: str, term: str):
        return urllib.request.urlopen(
            urllib.request.Request(
                url.format(term.replace(" ", "+")),
                headers=WorkshopWebScraper.headers,
            )
        )

    @classmethod
    def detail(cls, steamid: int):
        results = BeautifulSoup(
            cls._request(cls.detail_query, str(steamid)),
            "html.parser",
        )

        details = results.find_all("div", class_="detailsStatRight")
        try:
            size = details[0].get_text()
        except IndexError:
            size = None
        try:
            created = details[1].get_text()
        except IndexError:
            created = None
        try:
            updated = details[2].get_text()
        except IndexError:
            updated = None
        try:
            description = results.find(
                "div", class_="workshopItemDescription"
            ).get_text()
        except AttributeError:
            description = None
        try:
            num_ratings = results.find("div", class_="numRatings").get_text()
        except AttributeError:
            num_ratings = None
        try:
            rating = re.search(
                "([1-5])(?:-star)",
                str(results.find("div", class_="fileRatingDetails").img),
            ).group(1)
        except AttributeError:
            rating = None

        return WorkshopResult(
            steamid,
            size=size,
            create_time=created,
            update_time=updated,
            description=description,
            num_rating=num_ratings,
            rating=rating,
        )

    @classmethod
    def search(cls, term: str) -> Generator[WorkshopResult, None, None]:
        results = BeautifulSoup(
            cls._request(cls.index_query, term),
            "html.parser",
        ).find_all("div", class_="workshopItem")

        for r in results:
            try:
                item_title = r.find("div", class_="workshopItemTitle").get_text()
                author_name = r.find("div", class_="workshopItemAuthorName").get_text()
                steamid = int(
                    re.search(r"\d+", r.find("a", class_="ugc")["href"]).group()
                )
            except (AttributeError, ValueError):
                continue
            yield WorkshopResult(steamid, name=item_title, author=author_name)


class Configuration:
    """
    [Paths]
    rimworld: somepath
    workshop: somepath

    [Options]
    use_human_readable_dirs: false
    ignore_git_directories: false

    [Rules]
    1: *vanilla* > *
    """

    pass


class PathFinder:
    DEFAULT_GAME_PATHS = [
        "~/GOG Games/RimWorld",
        "~/.local/share/Steam/steamapps/common/RimWorld",
        "/Applications/Rimworld.app/Mods",
        "~/Library/Application Support/Steam/steamapps/common/RimWorld",
    ]

    DEFAULT_WORKSHOP_PATHS = ["~/.local/share/Steam/steamapps/workshop/content/294100"]

    DEFAULT_CONFIG_PATHS = [
        "~/Library/Application Support/Rimworld/",
        "~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios",
    ]

    @staticmethod
    def _is_game_dir(p: Path) -> bool:
        if p.name == "Mods":
            for n in p.parent.iterdir():
                if n.name == "Version.txt":
                    return True
        return False

    @staticmethod
    def _is_workshop_dir(p: Path) -> bool:
        return (
            p.name == "294100"
            and p.parts[-2] == "content"
            and p.parts[-3] == "workshop"
        )

    @staticmethod
    def _is_config_dir(p: Path) -> bool:
        files_to_find = ["Config", "prefs", "Saves"]
        child_names = [f.name for f in p.iterdir()]
        for target_name in files_to_find:
            if not target_name in child_names:
                return False
        return True

    @staticmethod
    def _search_root(p: Path, f) -> Optional[Path]:
        p = p.expanduser()
        for n in p.glob("**/"):
            if f(n):
                return n
        return None

    @staticmethod
    def get_workshop_from_game_path(p: Path):
        p = p.expanduser()
        for index, dirname in enumerate(p.parts):
            if dirname == "steamapps":
                return Path(*list(p.parts[0:index])) / Path(
                    "steamapps/workshop/content/294100"
                )

    @staticmethod
    def _search_defaults(defaults: list[str], f) -> Optional[Path]:
        for p in defaults:
            if p := f(Path(p)):
                return p
        return None

    @classmethod
    def find_game(cls, p: Path) -> Optional[Path]:
        return cls._search_root(p, cls._is_game_dir)

    @classmethod
    def find_workshop(cls, p: Path) -> Optional[Path]:
        return cls._search_root(p, cls._is_workshop_dir)

    @classmethod
    def find_config(cls, p: Path) -> Optional[Path]:
        return cls._search_root(p, cls._is_config_dir)

    @classmethod
    def find_game_defaults(cls) -> Optional[Path]:
        return cls._search_defaults(cls.DEFAULT_GAME_PATHS, cls.find_game)

    @classmethod
    def find_workshop_defaults(cls) -> Optional[Path]:
        return cls._search_defaults(cls.DEFAULT_WORKSHOP_PATHS, cls.find_workshop)

    @classmethod
    def find_config_defaults(cls) -> Optional[Path]:
        return cls._search_defaults(cls.DEFAULT_CONFIG_PATHS, cls.find_config)


class ModsConfig:
    def __init__(self, p: Path):
        self.path = p.expanduser()
        self.element_tree = ET.parse(self.path)
        self.root = self.element_tree.getroot()
        enabled = XMLUtil.list_grab("activeMods", self.root)
        self.mods = [Mod(pid) for pid in enabled]
        self.version = XMLUtil.element_grab("version", self.root)
        self.length = len(self.mods)

    def write(self):
        active_mods = self.root.find('activeMods')
        for item in list(active_mods.findall('li')):
            active_mods.remove(item)

        for mod in self.mods:
            new_element = ET.SubElement(active_mods, 'li')
            new_element.text = mod.packageid

        sbuffer = ET.tostring(self.root, 'utf-8').decode()
        sbuffer = str(re.sub(r"[\n\t\s]*", "", str(sbuffer)))
        minidom.parseString(sbuffer)
        print(
            minidom.parseString(sbuffer)
            .toprettyxml(indent="  ", newl="\n")
        )

    def enable_mod(self, m: Mod):
        self.mods.append(m)

    def remove_mod(self, m: Mod):
        for k,v in enumerate(self.mods):
            if self.mods[k] == m:
                del self.mods[k]


class DefAnalyzer:
    pass


class CLI:
    pass


class GraphAnalyzer:
    @staticmethod
    def graph(mods):
        import networkx as nx
        import pyplot as plt

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
            DG,
            pos,
            node_size=100,
            alpha=0.8,
            edge_color="r",
            font_size=8,
            with_labels=True,
        )
        ax = plt.gca()
        ax.margins(0.08)

        print("topological sort:")
        sorted = list(nx.topological_sort(DG))
        for n in sorted:
            print(n)

        plt.show()


if __name__ == "__main__":
    # Create test mod list
    # mods = ModFolderReader.create_mods_list(
    #     Path("/tmp/rmm/.steam/steamapps/workshop/content/294100/")
    # )
    # print(mods)

    # print(PathFinder.search_game_root(Path('~/')))
    print(
        PathFinder.get_workshop_from_game_path(
            Path("~/.local/share/Steam/steamapps/common/RimWorld")
        )
    )
    print(
        PathFinder.get_workshop_from_game_path(
            Path("~/.local/share/Steam/steamapps/workshop/content/294100")
        )
    )
    test = ModsConfig(PathFinder.find_config_defaults() / "Config/ModsConfig.xml")
    test.remove_mod(Mod('fluffy.desirepaths'))
    test.write()

    # ModListStreamer.write(Path("/tmp/test_modlist"), mods, ModListV1Format())
    # print(len(  ModListStreamer.read(Path("/tmp/test_modlist"), ModListV1Format()) ) )

    # results = list( WorkshopWebScraper.search("rimhud") )
    # for n in range(1):
    #     print( results[n].get_details() )
    #     print()
