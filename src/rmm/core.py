#!/bin/python3
"""
RimWorld Mod Manager

Usage:
  rmm export [options] <file>
  rmm import [options] <file>
  rmm list [options]
  rmm migrate [options]
  rmm query [options] [<term>...]
  rmm remove [options] [<term>...]
  rmm search <term>...
  rmm sync [options] <name>...
  rmm update [options]
  rmm -h | --help
  rmm -v | --version

Operations:
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

Options:
  -p --path DIR     RimWorld path.
  -w --workshop DIR Workshop Path.
"""

from __future__ import annotations
import os
import sys
from typing import Iterable, cast, Optional
import xml.etree.ElementTree as ET
import requests as req
import argparse
import tempfile
import pathlib
import docopt

from enum import Enum
from bs4 import BeautifulSoup
from rmm.utils.processes import execute, run_sh


RMM_VERSION = "0.0.4"

DEFAULT_GAME_PATHS = [
    "~/GOG Games/RimWorld",
    "~/.local/share/Steam/steamapps/common/RimWorld",
]


class InvalidSelectionException(Exception):
    pass


class Mod:
    def __init__(self, name, steamid, versions, author, fp, ignore=False):
        self.name = name
        self.versions = versions
        self.author = author
        self.steamid = steamid
        self.fp = fp
        self.ignore = ignore

    def __repr__(self):
        return "<Mod name:{} author:{} steamid:{} dir:{} ignore:{}>".format(
            self.name, self.author, self.steamid, os.path.basename(self.fp), self.ignore
        )

    def __cell__(self):
        return [
            self.name,
            self.author,
            self.steamid,
            os.path.basename(self.fp),
            self.ignore,
        ]

    def remove(self):
        if self.ignore:
            return
        run_sh(f"rm -rf {self.fp}")

    def install(self, install_path):
        if self.ignore:
            return
        else:
            new_path = os.path.join(install_path, str(self.steamid))
            run_sh(f"cp -r {self.fp} {new_path}")

    def update_parent_dir(self, new_path):
        self.fp = os.path.join(new_path, str(self.steamid))
        self.check_for_ignore()

    def check_for_ignore(self):
        if os.path.isfile(os.path.join(self.fp, ".rmm_ignore")):
            self.ignore = True
        else:
            self.ignore = False

    @classmethod
    def create_from_path(cls, filepath) -> Optional[Mod]:
        try:
            tree = ET.parse(os.path.join(filepath, "About/About.xml"))
            root = tree.getroot()
            name = root.find("name").text
            author = root.find("author").text
            try:
                versions = [
                    v.text for v in root.find("supportedVersions").findall("li")
                ]
            except AttributeError:
                versions = None
        except FileNotFoundError as e:
            # print(e)
            # print(os.path.basename(filepath) + " is not a mod. Ignoring.")
            return None

        try:
            with open(os.path.join(filepath, "About/PublishedFileId.txt")) as f:
                steamid = f.readline().strip()
        except FileNotFoundError:
            steamid = None

        ignore = False
        if os.path.isfile(os.path.join(filepath, ".rmm_ignore")):
            ignore = True
        return Mod(name, steamid, versions, author, filepath, ignore=ignore)


class ModList:
    @classmethod
    def _get_mods_list(cls, path: str, f: Iterable) -> list[Mod]:
        return list(
            filter(
                None,
                map(
                    lambda d: Mod.create_from_path(os.path.join(path, d)),
                    f,
                ),
            )
        )

    @classmethod
    def get_mods_list_by_path(cls, path: str) -> list[Mod]:
        return cls._get_mods_list(path, os.listdir(path))

    @classmethod
    def get_mods_list_filter_by_id(cls, path: str, mods: list[int]) -> list[Mod]:
        return cls._get_mods_list(path, [str(m) for m in mods])

    @classmethod
    def get_mods_list_names(cls, mods: list[Mod]) -> list[str]:
        return [n.name for n in mods]

    @classmethod
    def get_by_id(cls, mods: list[Mod], steamid: int):
        for n in mods:
            if n.steamid == steamid:
                return n
        return None

    @classmethod
    def to_int_list(cls, mods: list[Mod]) -> list[int]:
        return list(filter(None, cast(list[int], [m.steamid for m in mods])))


class ModListFile:
    @classmethod
    def read_text_modlist(cls, path: str) -> list[int]:
        mods = []
        with open(path) as f:
            for line in f:
                itemid = line.split("#", 1)[0]
                try:
                    mods.append(int(itemid))
                except ValueError:
                    continue
        return mods

    @classmethod
    def export_text_modlist(cls, mods: list[Mod], human_format: bool = True) -> str:
        output = ""
        for m in mods:
            if human_format:
                output += "{} #{} by {}\n".format(m.steamid, m.name, m.author)
            else:
                output += "{}".format(m.steamid)
        return output

    @classmethod
    def write_text_modlist(cls, mods: list[Mod], path: str) -> None:
        with open(path, "w") as f:
            f.write(cls.export_text_modlist(mods))


class SteamDownloader:
    @classmethod
    def download(cls, mods, folder):
        def workshop_format(mods):
            return (s := " +workshop_download_item 294100 ") + s.join(
                str(x) for x in mods
            )

        query = 'env HOME="{}" steamcmd +login anonymous "{}" +quit >&2'.format(
            folder, workshop_format(mods)
        )
        run_sh(query)
        print()

    @classmethod
    def download_modlist(cls, mods, path):
        steamids = [n.steamid for n in mods]
        return cls.download(steamids, path)


class WorkshopResultsEnum(Enum):
    TITLE = 0
    AUTHOR = 1
    STEAMID = 2


class WorkshopWebScraper:
    @classmethod
    def scrape_update_date(cls, mod):
        resp = req.get(
            "https://steamcommunity.com/sharedfiles/filedetails/?id={}".format(
                mod.steamid
            )
        )
        soup = BeautifulSoup(resp.content, "html.parser")
        return list(soup.find_all("div", class_="detailsStatRight"))[2].get_text()

    @classmethod
    def workshop_search(cls, name):
        name = name.replace(" ", "+")
        resp = req.get(
            "https://steamcommunity.com/workshop/browse/?appid=294100&searchtext={}".format(
                name
            )
        )
        soup = BeautifulSoup(resp.content, "html.parser")
        items = soup.find_all("div", class_="workshopItem")
        results = []
        import re

        for n in items:
            item_title = n.find("div", class_="workshopItemTitle").get_text()
            author_name = n.find("div", class_="workshopItemAuthorName").get_text()
            steamid = int(re.search(r"\d+", n.find("a", class_="ugc")["href"]).group())
            results.append((item_title, author_name, steamid))
        return results


class Manager:
    def __init__(self, moddir, workshop_path):
        self.workshop_path = workshop_path
        self.moddir = moddir
        self.cachedir = None

        for dirs in os.listdir("/tmp"):
            if (
                dirs[0:4] == "rmm-"
                and os.path.isdir(os.path.join("/tmp", dirs))
                and ".rmm" in os.listdir(os.path.join("/tmp", dirs))
            ):
                self.cachedir = os.path.join("/tmp", dirs)

        if not self.cachedir:
            self.cachedir = tempfile.mkdtemp(prefix="rmm-")
            with open(os.path.join(self.cachedir, ".rmm"), "w"):
                pass

        self.cache_content_dir = os.path.join(
            self.cachedir, ".steam/steamapps/workshop/content/294100/"
        )

    def get_mods_as_list(self) -> list[Mod]:
        if (
            self.workshop_path
            and (workshop_mods := self.get_mods_as_list_workshop()) is not None
        ):
            return self.get_mods_as_list_native() + workshop_mods
        return self.get_mods_as_list_native()

    def get_mods_as_list_workshop(self) -> list[Mod]:
        return ModList.get_mods_list_by_path(self.workshop_path)

    def get_mods_as_list_native(self) -> list[Mod]:
        return ModList.get_mods_list_by_path(self.moddir)

    def get_mods_names(self) -> list[str]:
        return ModList.get_mods_list_names(self.get_mods_as_list())

    def backup_mod_dir(self, tarball_fp):
        query = '(cd {}; tar -vcaf "{}" ".")'.format(self.moddir, tarball_fp)
        for line in execute(query):
            print(line, end="")

    def sync_mod_list(self, mod_list: list[int], force_native: bool = False) -> bool:
        SteamDownloader().download(mod_list, self.cachedir)
        mods = ModList.get_mods_list_filter_by_id(self.cache_content_dir, mod_list)
        current_mods = self.get_mods_as_list_native()
        workshop_mods = None
        if self.workshop_path:
            workshop_mods = self.get_mods_as_list_workshop()
        for n in mods:
            install_path = self.moddir

            mod_native = None
            if mod_native := (ModList.get_by_id(current_mods, n.steamid)):
                if mod_native.ignore:
                    print(f"Skipping {mod_native.name} due to ignore file")
                    continue
                mod_native.remove()
            mod_workshop = None
            if self.workshop_path and (
                mod_workshop := (ModList.get_by_id(workshop_mods, n.steamid))
            ):
                if mod_workshop.ignore:
                    print(f"Skipping {mod_workshop.name} due to ignore file")
                    continue
                mod_workshop.remove()
                if not force_native:
                    install_path = self.workshop_path

            install_path_mod = os.path.join(install_path, n.steamid)
            if os.path.isdir(install_path_mod) and not os.path.isfile(
                os.path.join(install_path_mod, ".rmm_ignore")
            ):
                print(
                    f"Name space collision at: {install_path_mod}\nWould you like to removal the conflicting directory? [y/n]"
                )

                s = ""
                while True:
                    if (s := input()) != "y" or s != "n":
                        print("Enter [y/n]")
                        continue
                    break
                if s != "y":
                    print("Skipping {m.name}")
                    continue
                else:
                    print("Removing directory...")
                    run_sh(f"rm -rf {install_path_mod}")

            print(f"Installing {n.name}")
            n.install(install_path)

        return True

    def sync_mod(self, steamid: int) -> bool:
        return self.sync_mod_list([steamid])

    def sync_mod_list_file(self, modlist_fp):
        return self.sync_mod_list(ModListFile.read_text_modlist(modlist_fp))

    def update_all_mods(self):
        self.sync_mod_list(ModList.to_int_list(self.get_mods_as_list()))

    def migrate_all_mods(self):
        self.sync_mod_list(
            ModList.to_int_list(self.get_mods_as_list()), force_native=True
        )

    def remove_mod_list(self, modlist: list[Mod]) -> bool:
        for m in modlist:
            print("Removing {} by {}...".format(m.name, m.author))
            m.remove()
        return True

    def get_mod_table(self):
        import tabulate

        return tabulate.tabulate(
            [m.__cell__() for m in self.get_mods_as_list()],
            headers=["Name", "Author", "SteamID", "Dir", "Ignored"],
        )


class CLI:
    def __init__(self):
        self.path = None
        self.workshop_path = None

        try:
            arguments = docopt.docopt(__doc__, version="RMM 0.0.4", more_magic=True)
        except docopt.DocoptExit:
            arguments = {}
            print(__doc__)
            if len(sys.argv) > 1:
                print("Invalid syntax. You may have too many or too little argument.")
                sys.exit(1)
            if len(sys.argv) > 0:
                sys.exit(0)

        def check_default_paths():
            for path in DEFAULT_GAME_PATHS:
                p = os.path.expanduser((os.path.join(path, "game", "Mods")))
                if os.path.isdir(p):
                    return p
            return None

        def find_game(path):
            if not os.path.basename(path) == "Mods":
                for root, dirs, files in os.walk(path):
                    if os.path.basename(root) == "game" and "Mods" in dirs:
                        # TODO read gameinfo file to ensure is actually rimworld
                        return os.path.join(root, "Mods")
            return None

        if arguments["--path"]:
            self.path = arguments["--path"]
            self.path = find_game(self.path)

        if not self.path:
            try:
                self.path = os.path.expanduser(os.environ["RMM_PATH"])
                self.path = find_game(self.path)
            except KeyError:
                self.path = None

        if not self.path:
            print("RimWorld mod directory not set.\n" "Trying default directories...")
            self.path = check_default_paths()

        if not self.path:
            print(
                "Game not found.\n"
                'Please set "RMM_PATH" variable to the RimWorld mod directory in your environment.\n'
                '\nexport RMM_PATH="~/games/rimworld"\nrmm list\n or \n'
                'RMM_PATH="~/games/rimworld" rmm list'
            )
            exit(1)

        print("rimworld path: {}".format(self.path))

        def find_workshop(path):
            if not os.path.basename(path) == "294100" and "Steam" in path:
                if os.path.isdir(
                    s := os.path.join(
                        "".join(path.partition("Steam/")[0:2]),
                        "steamapps/workshop/content/294100",
                    )
                ):
                    return path
                return None

        def find_workshop_from_game_path(path):
            if "/Steam/steamapps/common" in path:
                if os.path.isdir(
                    s := os.path.join(
                        "".join(path.partition("/Steam/steamapps")[0:2]),
                        "workshop/content/294100",
                    )
                ):
                    return s
            return None

        if arguments["--workshop"]:
            self.workshop_path = arguments["--workshop"]
        else:
            try:
                self.workshop_path = os.path.expanduser(os.environ["RMM_WORKSHOP_PATH"])
            except KeyError as err:
                self.workshop_path = None

        if self.workshop_path:
            self.workshop_path = find_workshop(self.workshop_path)
        else:
            self.workshop_path = find_workshop_from_game_path(self.path)

        if self.workshop_path:
            print(f"workshop path: {self.workshop_path}\n")
        else:
            print(f"workshop path {self.workshop_path} not found. ignoring.")
            self.workshop_path = None

        for command in [
            "export",
            "import",
            "list",
            "migrate",
            "query",
            "remove",
            "search",
            "sync",
            "update",
        ]:
            if arguments[command] == True:
                getattr(self, command)(arguments)

    def search(self, arguments):
        results = WorkshopWebScraper.workshop_search(" ".join(arguments["<term>"]))
        from tabulate import tabulate

        print(tabulate(reversed(results)))

    def export(self, arguments):
        mods = Manager(self.path, self.workshop_path).get_mods_as_list()
        if arguments["<file>"] != "-":
            ModListFile.write_text_modlist(mods, arguments["<file>"])
            print("Mod list written to {}.\n".format(arguments["<file>"]))
        else:
            print(ModListFile.export_text_modlist(mods))

    def list(self, arguments):
        if not (s := Manager(self.path, self.workshop_path).get_mod_table()):
            print("No mods installed. Add them using the 'sync' command.")
        else:
            print(s)

    def _import(self, arguments):
        file = arguments["<file>"]
        Manager(self.path, self.workshop_path).sync_mod_list_file(file)

    def sync(self, arguments):
        search_term = " ".join(arguments["<name>"])

        results = WorkshopWebScraper.workshop_search(search_term)
        for n, element in enumerate(reversed(results)):
            n = abs(n - len(results))
            print(
                "{}. {} {}".format(
                    n,
                    element[WorkshopResultsEnum.TITLE.value],
                    element[WorkshopResultsEnum.AUTHOR.value],
                )
            )
        print("Packages to install (eg: 1 2 3, 1-3 or ^4)")

        while True:
            try:
                selection = int(input()) - 1
                if selection >= len(results) or selection < 0:
                    raise InvalidSelectionException("Out of bounds")
                break
            except ValueError:
                print("Must enter valid integer")
            except InvalidSelectionException:
                print("Selection out of bounds.")

        print(
            "Package(s): {} will be installed. Continue? [y/n] ".format(
                results[selection][WorkshopResultsEnum.TITLE.value]
            ),
            end="",
        )

        if input() != "y":
            return False

        Manager(self.path, self.workshop_path).sync_mod(
            results[selection][WorkshopResultsEnum.STEAMID.value]
        )
        print("Package installation complete.")

    def install(self, arguments):
        self.sync(arguments)

    def update(self, arguments):
        print(
            "Preparing to update following packages: "
            + ", ".join(
                str(x) for x in Manager(self.path, self.workshop_path).get_mods_names()
            )
            + "\n\nWould you like to continue? [y/n]"
        )

        if input() != "y":
            return False

        Manager(self.path, self.workshop_path).update_all_mods()
        print("Package update complete.")

    def migrate(self, arguments):
        print(
            "RMM is going to migrate your Steam Workshop mods to the game's native Mods directory. The following packages will be migrated: "
            + ", ".join(
                str(x) for x in Manager(self.path, self.workshop_path).get_mods_names()
            )
            + "\n\nWould you like to continue? [y/n]"
        )

        if input() != "y":
            return False

        Manager(self.path, self.workshop_path).migrate_all_mods()
        print(
            "Migration complete. To complete the migration go to https://steamcommunity.com/app/294100/workshop/\nNavigate to Browse->Subscribed Items. Then select 'Unsubscribe From All'"
        )

    def backup(self, arguments):
        print("Backing up mod directory to '{}.\n".format(arguments["<file>"]))
        Manager(self.path, self.workshop_path).backup_mod_dir(arguments["<file>"])
        print("Backup completed to " + arguments["<file>"])

    def remove(self, arguments):
        search_term = " ".join(arguments["<term>"])
        search_result = [
            r
            for r in Manager(self.path, self.workshop_path).get_mods_as_list()
            if str.lower(search_term) in str.lower(r.name)
            or str.lower(search_term) in str.lower(r.author)
            or search_term == r.steamid
        ]

        if not search_result:
            print(f"No packages matching {search_term}")
            return False

        for n, element in enumerate(reversed(search_result)):
            n = abs(n - len(search_result))
            print(
                "{}. {} by {}".format(
                    n,
                    element.name,
                    element.author,
                )
            )
        print("Packages to remove (eg: 1 2 3, 1-3 or ^4)")

        def expand_ranges(s):
            import re

            return re.sub(
                r"(\d+)-(\d+)",
                lambda match: " ".join(
                    str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)
                ),
                s,
            )

        while True:
            try:
                selection = input()
                selection = [int(s) for s in expand_ranges(selection).split(" ")]
                for n in selection:
                    if n > len(search_result) or n <= 0:
                        raise InvalidSelectionException("Out of bounds")
                break
            except ValueError:
                print("Must enter valid integer or range")
            except InvalidSelectionException:
                print("Selection out of bounds.")

        remove_queue = [search_result[m - 1] for m in selection]
        print("Would you like to remove? ")
        for m in remove_queue:
            print("{} by {}".format(m.name, m.author))

        print("[y/n]: ", end="")

        if input() != "y":
            return False

        Manager(self.path, self.workshop_path).remove_mod_list(remove_queue)

    def query(self, arguments):
        search_term = " ".join(arguments["<term>"])

        search_result = [
            r
            for r in Manager(self.path, self.workshop_path).get_mods_as_list()
            if str.lower(search_term) in str.lower(r.name)
            or str.lower(search_term) in str.lower(r.author)
            or search_term == r.steamid
        ]
        if not search_result:
            print(f"No packages matching {search_term}")
            return False
        for n, element in enumerate(reversed(search_result)):
            n = abs(n - len(search_result))
            print(
                "{}. {} by {}".format(
                    n,
                    element.name,
                    element.author,
                )
            )

    def version(self):
        version_string = f"""rmm {RMM_VERSION}
Copyright (C) 2021 Michael Ciociola
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law."""
        print(version_string)


def run():
    t = CLI()


if __name__ == "__main__":
    run()
