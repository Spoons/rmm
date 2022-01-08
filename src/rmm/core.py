#!/bin/python3
from __future__ import annotations

import csv
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
import tempfile
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Callable, Generator, Iterable, Iterator, Optional, cast
from xml.dom import minidom

import tabulate
from bs4 import BeautifulSoup

class InvalidSelectionException(Exception):
    pass


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
        unixes = ["linux", "darwin", "freebsd"]

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
    def list_grab(element: str, root: ET.Element) -> Optional[list[str]]:
        try:
            return cast(
                Optional[list[str]],
                [n.text for n in cast(ET.Element, root.find(element)).findall("li")],
            )
        except AttributeError:
            return None

    @staticmethod
    def element_grab(element: str, root: ET.Element) -> Optional[str]:
        try:
            return cast(ET.Element, root.find(element)).text
        except AttributeError:
            return None

    @staticmethod
    def et_pretty_xml(root: ET.Element) -> str:
        return minidom.parseString(
            re.sub(
                r"[\n\t\s]*",
                "",
                (ET.tostring(cast(ET.Element, root), "utf-8").decode()),
            )
        ).toprettyxml(indent="  ", newl="\n")


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
                    return int((path / "About" / "PublishedFileId.txt").read_text().strip().encode("ascii", errors="ignore").decode())
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

    def insert(self, i, x) -> None:
        self.data[i] = x

    def __repr__(self):
        return f"<ModList: {self.data.__repr__()}>"


class ModFolderReader:
    @staticmethod
    def create_mods_list(path: Path) -> ModList:
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
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        pass

    @classmethod
    @abstractmethod
    def serialize(cls, mods: MutableSequence) -> Generator[str, None, None]:
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
                yield Mod(
                    None,
                    steamid=int(parsed[cls.STEAM_ID]),
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
    @staticmethod
    def download(mods: list[int]) -> tuple[ModList, Path]:
        home_path = None
        mod_path = None
        for d in Path("/tmp").iterdir():
            if d.name[0:4] == "rmm-" and d.is_dir() and (d / ".rmm").is_file():
                home_path = d
                break

        if not home_path:
            home_path = Path(tempfile.mkdtemp(prefix="rmm-"))
            with open((home_path / ".rmm"), "w"):
                pass

        if not home_path:
            raise Exception("Error could not get temporary directory")

        home_path = cast(Path, home_path)
        mod_path = home_path / ".steam/steamapps/workshop/content/294100/"
        mod_path = cast(Path, mod_path)

        workshop_item_arg = " +workshop_download_item 294100 "
        query = 'env HOME="{}" steamcmd +login anonymous "{}" +quit >&2'.format(
            str(home_path), workshop_item_arg + workshop_item_arg.join(str(m) for m in mods)
        )
        Util.run_sh(query)

        return (ModFolderReader.create_mods_list(mod_path), mod_path)


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
    def search(cls, term: str, details: bool = False) -> Generator[WorkshopResult, None, None]:
        results = BeautifulSoup(
            cls._request(cls.index_query, term),
            "html.parser",
        ).find_all("div", class_="workshopItem")

        for r in results:
            try:
                item_title = r.find("div", class_="workshopItemTitle").get_text()
                author_name = r.find("div", class_="workshopItemAuthorName").get_text()[3:]
                steamid = int(
                    re.search(r"\d+", r.find("a", class_="ugc")["href"]).group()
                )
            except (AttributeError, ValueError):
                continue
            result = WorkshopResult(steamid, name=item_title, author=author_name)
            if details:
                print("grabbing " + item_title)
                detailsResult = WorkshopWebScraper.detail(steamid)
                if detailsResult:
                    result._merge(detailsResult)
            yield result


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


class Config:
    def __init__(
        self, path: Optional[Path] = None, workshop_path: Optional[Path] = None
    ):
        self.path = cast(Path, path)
        self.workshop_path = workshop_path


class ModsConfig:
    def __init__(self, p: Path):
        if isinstance(p, str):
            p = Path(p)
        self.path = p.expanduser()
        try:
            self.element_tree = ET.parse(self.path)
        except OSError:
            print("Unable to read ModsConfig file at " + str(self.path))
            raise

        self.root = self.element_tree.getroot()
        try:
            enabled = cast(
                list[str],
                XMLUtil.list_grab("activeMods", cast(ET.ElementTree, self.root)),
            )
            self.mods = [Mod(pid) for pid in enabled]
        except TypeError:
            print("Unable to parse activeMods in ModsConfig")
            raise
        self.version = XMLUtil.element_grab("version", self.root)
        self.length = len(self.mods)

    def write(self):
        active_mods = self.root.find("activeMods")
        try:
            for item in list(active_mods.findall("li")):
                active_mods.remove(item)
        except AttributeError:
            pass

        try:
            for mod in self.mods:
                new_element = ET.SubElement(active_mods, "li")
                new_element.text = mod.packageid
        except AttributeError:
            raise Exception("Unable to find 'activeMods' in ModsConfig")

        buffer = XMLUtil.et_pretty_xml(self.root)
        print(buffer)

        try:
            with self.path.open("w+") as f:
                f.seek(0)
                f.write(buffer)
        except OSError:
            print("Unable to write ModsConfig")
            raise

    def enable_mod(self, m: Mod):
        self.mods.append(m)

    def remove_mod(self, m: Mod):
        for k, v in enumerate(self.mods):
            if self.mods[k] == m:
                del self.mods[k]


class DefAnalyzer:
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


class CLI:
    @staticmethod
    def tabulate_mods(mods: ModList) -> str:
        return tabulate.tabulate(
            [[n.name, n.author[:20], n.steamid, n.ignored, n.path.name] for n in mods],
            headers=["name", "author", "steamid", "ignored", "folder"],
        )

    @staticmethod
    def __get_long_name_from_alias_map(word, _list):
        for item in _list:
            if isinstance(item, tuple):
                if word in list(item):
                    return item[0]
            if isinstance(item, str):
                if word == item:
                    return word
        return None

    @staticmethod
    def parse_options() -> Config:
        path_options = [("path", "--path", "-p"), ("workshop_path", "--workshop", "-w")]


        config = Config()
        del sys.argv[0]
        try:
            while s := CLI.__get_long_name_from_alias_map(
                sys.argv[0], [p for p in path_options]
            ):
                del sys.argv[0]
                setattr(config, s, Path(sys.argv[0]))
                del sys.argv[0]
        except IndexError:
            pass

        return config

    @staticmethod
    def help(args: list, config: Config):
        print(Useage.__doc__)

    @staticmethod
    def version(args: list, config: Config):
        try:
            print(importlib.metadata.version("rmm-spoons"))
        except importlib.metadata.PackageNotFoundError:
            print("version unknown")

    @staticmethod
    def _list(args, config: Config):
        print(CLI.tabulate_mods(ModFolderReader.create_mods_list(config.path)))

    @staticmethod
    def query(args, config: Config):
        search_term = " ".join(args[1:])
        print(
            CLI.tabulate_mods(
                ModList(
                    [
                        r
                        for r in ModFolderReader.create_mods_list(config.path)
                        if str.lower(search_term) in str.lower(r.name)
                        or str.lower(search_term) in str.lower(r.author)
                        or search_term == r.steamid
                    ]
                )
            )
        )

    @staticmethod
    def search(args: list[str], config: Config):
        results = reversed(list(WorkshopWebScraper.search(" ".join(args[1:]))))
        print(tabulate.tabulate([[r.name, r.author, r.num_ratings, r.description] for r in results]))

    @staticmethod
    def sync(args: list[str], config: Config):
        results = list(reversed(list(WorkshopWebScraper.search(" ".join(args[1:])))))
        print(tabulate.tabulate([[len(results)-k, r.name, r.author, r.num_ratings, r.description] for k,r in enumerate(results)]))
        print("Packages to install (eg: 2)")

        while True:
            try:
                selection = len(results) - int(input())
                if selection >= len(results) or selection < 0:
                    raise InvalidSelectionException("Out of bounds")
                break
            except ValueError:
                print("Must enter valid integer")
            except InvalidSelectionException:
                print("Selection out of bounds.")

        # print(
        #     "Package(s): {} will be installed. Continue? [y/n] ".format(
        #         results[selection].name
        #     ),
        #     end="",
        # )

        (mods, path) = SteamDownloader.download([results[selection].steamid])



    @staticmethod
    def run():
        config = CLI.parse_options()
        if config.path:
            config.path = PathFinder.find_game(config.path)
        if not config.path:
            try:
                config.path = PathFinder.find_game(Path(os.environ["RMM_PATH"]))
            except KeyError:
                config.path = PathFinder.find_game_defaults()

        if config.workshop_path:
            config.workshop_path = PathFinder.find_workshop(Path(config.workshop_path))

        if not config.workshop_path:
            try:
                config.workshop_path = PathFinder.find_workshop(
                    Path(os.environ["RMM_WORKSHOP_PATH"])
                )
            except KeyError:
                if config.path:
                    config.workshop_path = PathFinder.get_workshop_from_game_path(
                        Path(config.path)
                    )
                else:
                    config.workshop_path = PathFinder.find_workshop_defaults()

        actions = [
            "backup",
            "export",
            ("_list", "list"),
            "query",
            "remove",
            "search",
            "sync",
            "update",
            ("help", "-h"),
            ("version", "-v"),
        ]
        try:
            if s := CLI.__get_long_name_from_alias_map(sys.argv[0], actions):
                getattr(CLI, s)(sys.argv, config)
        except IndexError:
            print(Useage.__doc__)
            sys.exit(0)


if __name__ == "__main__":
    CLI.run()

    # Create test mod list
    # mods = ModFolderReader.create_mods_list(PathFinder.find_game(Path("~/games")))
    # print(mods)

    # print(
    #     PathFinder.get_workshop_from_game_path(
    #         Path("~/.local/share/Steam/steamapps/common/RimWorld")
    #     )
    # )
    # test = ModsConfig(PathFinder.find_config_defaults() / "Config/ModsConfig.xml")
    # test.remove_mod(Mod("fluffy.desirepaths"))
    # test.write()

    # ModListStreamer.write(Path("/tmp/test_modlist"), mods, ModListV1Format())
    # print(len(ModListStreamer.read(Path("/tmp/test_modlist"), ModListV1Format())))

    # results = list(WorkshopWebScraper.search("rimhud"))
    # for n in range(1):
    #     print(results[n].get_details())
    #     print()
