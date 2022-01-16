#!/bin/python3
from __future__ import annotations

import re
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, cast

from bs4 import BeautifulSoup

import util
from config import Config
from mod import Mod, ModFolder

EXPANSION_PACKAGES = [
    Mod(packageid="ludeon.rimworld"),
    Mod(packageid="ludeon.rimworld.ideology"),
    Mod(packageid="ludeon.rimworld.royalty"),
]

class Manager():
    def __init__(self, config: Config):
        if not isinstance(config, Config):
            raise Exception("Must pass Config object to Manager")
        self.config = config
        if self.config.modsconfig_path:
            self.modsconfig = ModsConfig(self.config.modsconfig_path)

    def install_mod(self, steam_cache: Path, steamid: int):
        if not steamid:
            raise Exception("Missing SteamID")
        mod = Mod.create_from_path(steam_cache / str( steamid ))

        dest_path = None
        if self.config.USE_HUMAN_NAMES and mod and mod.packageid:
            dest_path = self.config.mod_path / mod.packageid
        else:
            dest_path = self.config.mod_path / str(steamid)

        if dest_path:
            util.copy(
                steam_cache / str(steamid),
                dest_path,
                recursive=True,
            )
        else:
            print(f"Unable to install mod: {steamid}")
            return False
        return True

    def remove_mod(self, mod: Mod):
        if not self.config.mod_path:
            raise Exception("Game path not defined")

        installed_mods = ModFolder.read(self.config.mod_path)
        print(installed_mods)
        removal_queue = [ n for n in installed_mods if n == mod ]
        print(removal_queue)

        for m in removal_queue:
            print(f"Uninstalling {mod.title()}")
            mod_absolute_path = self.config.mod_path / m.dirname
            print(mod_absolute_path)
            if (mod_absolute_path):
                util.remove(mod_absolute_path)

            steamid_path = self.config.mod_path / str( m.steamid )
            if m.steamid and steamid_path.exists():
                util.remove(self.config.mod_path / str(m.steamid))

            pid_path = self.config.mod_path / m.packageid
            if self.config.USE_HUMAN_NAMES and m.packageid and pid_path.exists():
                util.remove(pid_path)


    def remove_mods(self, queue: list[Mod]):
        for mod in queue:
            if isinstance(mod, WorkshopResult):
                mod = Mod.create_from_workshorp_result(mod)
            self.remove_mod(mod)


    def sync_mods(self,queue: list[Mod]|list[WorkshopResult]):
        (_, steam_cache_path) = SteamDownloader.download([ mod.steamid for mod in queue if mod.steamid ])
        # game_dir_mods = ModFolder.read(config.game_path)

        for mod in queue:
            if isinstance(mod, WorkshopResult):
                mod = Mod.create_from_workshorp_result(mod)
            if not isinstance(mod.steamid, int):
                continue
            success = False
            try_install = False
            try:
                self.remove_mod(mod)
                success = self.install_mod(steam_cache_path, mod.steamid)
            except FileNotFoundError:
                print(f"Unable to download and install {mod.title()}\n\tDoes this mod still exist?")
            if success:
                print(f"Installed {mod.title()}")

    def installed_mods(self):
        return ModFolder.read(self.config.mod_path)

    def search_installed(self, term):
        return ModFolder.search(self.config.mod_path, term)

    def enabled_mods(self):
        return self.modsconfig.mods

    def disabled_mods(self):
        enabled_mods = self.enabled_mods()
        installed_mods = self.installed_mods()
        return util.list_loop_exclusion(installed_mods, enabled_mods)

class SteamDownloader:
    @staticmethod
    def download(mods: list[int]) -> tuple[list[Mod], Path]:
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
            str(home_path),
            workshop_item_arg + workshop_item_arg.join(str(m) for m in mods),
        )
        util.run_sh(query)

        return (ModFolder.read(mod_path), mod_path)


class WorkshopResult:
    def __init__(
        self,
        steamid,
        name=None,
        author=None,
        description=None,
        update_time=None,
        size=None,
        # num_rating=None,
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

    def __eq__(self, other: object) -> bool:
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
    def detail(cls, steamid: int) -> WorkshopResult:
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
            )
            if description:
                description = description.get_text()
        except AttributeError:
            description = None
        try:
            num_ratings = results.find("div", class_="numRatings")
            if num_ratings:
                num_ratings = num_ratings.get_text()
        except AttributeError:
            num_ratings = None
        try:
            rating = re.search(
                "([1-5])(?:-star)",
                str(results.find("div", class_="fileRatingDetails").img),
            )
            if rating:
                rating = rating.group(1)
        except AttributeError:
            rating = None

        return WorkshopResult(
            steamid,
            size=size,
            create_time=created,
            update_time=updated,
            description=description,
            # num_rating=num_ratings,
            rating=rating,
        )

    @classmethod
    def search(cls, term: str, reverse: bool = False) -> list[WorkshopResult]:
        page_result = BeautifulSoup(
            cls._request(cls.index_query, term),
            "html.parser",
        ).find_all("div", class_="workshopItem")

        results = []
        for r in page_result:
            try:
                item_title = r.find("div", class_="workshopItemTitle").get_text()
                author_name = r.find("div", class_="workshopItemAuthorName").get_text()[
                    3:
                ]
                steamid = int(
                    re.search(r"\d+", r.find("a", class_="ugc")["href"]).group()
                )
            except (AttributeError, ValueError):
                continue
            results.append(WorkshopResult(steamid, name=item_title, author=author_name))

        if reverse:
            return list(reversed(results))
        return results


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
                util.list_grab("activeMods", self.root),
            )
            self.mods = [Mod(packageid=pid) for pid in enabled]
        except TypeError:
            print("Unable to parse activeMods in ModsConfig")
            raise
        self.version = util.element_grab("version", self.root)
        self.length = len(self.mods)

    def write(self):
        active_mods = self.root.find("activeMods")
        if not active_mods:
            return
        try:
            for item in list(active_mods.findall("li")):
                if active_mods:
                    active_mods.remove(item)
        except AttributeError:
            pass

        try:
            for mod in self.mods:
                new_element = ET.SubElement(active_mods, "li")
                new_element.text = mod.packageid
        except AttributeError:
            raise Exception("Unable to find 'activeMods' in ModsConfig")

        buffer = util.et_pretty_xml(self.root)

        try:
            with self.path.open("w+") as f:
                f.seek(0)
                f.write(buffer)
        except OSError:
            print("Unable to write ModsConfig")
            raise

    def expansions(self):
        pass

    def enable_mod(self, m: Mod):
        self.mods.append(m)

    def remove_mod(self, m: Mod):
        for k, _ in enumerate(self.mods):
            if self.mods[k] == m:
                del self.mods[k]

    def autosort(self, mods, config):
        import json

        import networkx as nx

        DG = nx.DiGraph()

        before_core = ['brrainz.harmony', 'me.samboycoding.betterloading']

        expansion_load_order = [
            "ludeon.rimworld",
            "ludeon.rimworld.royalty",
            "ludeon.rimworld.ideology",
        ]

        combined_load_order = before_core + expansion_load_order
        for n, pid in enumerate(combined_load_order):
            if pid not in self.mods:
                del combined_load_order[n]

        for k in range(0, len(combined_load_order)):
            for j in range(k + 1, len(combined_load_order)):
                DG.add_edge(combined_load_order[j], combined_load_order[k])

        populated_mods = [m for m in mods if m in self.mods]

        with (config.game_path / "1847679158/db/communityRules.json").open("r") as f:
            community_db = json.load(f)

        for pid in populated_mods:
            try:
                for j in community_db["rules"][pid.packageid]["loadAfter"]:
                    if j:
                        try:
                            pid.before.add(j)
                        except AttributeError:
                            pid.before = set(j)
            except KeyError:
                pass
            try:
                for j in community_db["rules"][pid.packageid]["loadBefore"]:
                    if j:
                        try:
                            pid.after.add(j)
                        except AttributeError:
                            pid.after = set(j)
            except KeyError:
                pass


        rocketman = False
        if "krkr.rocketman" in populated_mods:
            rocketman = True

        if "murmur.walllight" in populated_mods and "juanlopez2008.lightsout" in populated_mods:
            DG.add_edge("juanlopez2008.lightsout", "murmur.walllight")

        for m in populated_mods:
            if rocketman and m.packageid != 'krkr.rocketman':
                DG.add_edge('krkr.rocketman', m.packageid)
            if not m in combined_load_order:
                for n in combined_load_order:
                    DG.add_edge(m.packageid, n)
            if m.after:
                for a in m.after:
                    if a in self.mods:
                        DG.add_edge(a.lower(), m.packageid)
            if m.before:
                for b in m.before:
                    if b in self.mods:
                        DG.add_edge(m.packageid, b.lower())

        count = 0
        while True:
            try:
                sorted_mods = reversed(list(nx.topological_sort(DG)))
                self.mods = [Mod(packageid=n) for n in sorted_mods]
                print("Auto-sort complete")
                return
            except nx.exception.NetworkXUnfeasible:
                if count >= 10:
                    print("Unable to break cycles")
                    exit(0)
                print("Cycle found. Breaking load order cycle")
                cycle = nx.find_cycle(DG)
                print(cycle)
                DG.remove_edge(*cycle[0])
                count += 1
