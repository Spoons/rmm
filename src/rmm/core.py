#!/usr/bin/env python3
import os
from posixpath import expanduser
import sys
from typing import Iterable
import xml.etree.ElementTree as ET
import requests as req
import argparse
import tempfile

from enum import Enum
from bs4 import BeautifulSoup
from rmm.utils.processes import execute, run_sh

DEFAULT_GAME_PATHS = [
    "~/GOG Games/RimWorld",
    "~/.local/share/Steam/steamapps/common/RimWorld",
]


class InvalidSelectionException(Exception):
    pass


class Mod:
    def __init__(self, name, steamid, versions, author, fp):
        self.name = name
        self.versions = versions
        self.author = author
        self.steamid = steamid
        self.fp = fp

    def __repr__(self):
        return "<Mod name:{} author:{} steamid:{} versions:{}>".format(
            self.name, self.author, self.steamid, self.versions
        )

    def __cell__(self):
        return [self.name, self.author, self.steamid, self.versions]

    def remove(self):
        run_sh(f"rm -r {self.fp}")

    def install(self, moddir):
        new_path = os.path.join(moddir, str(self.steamid))
        run_sh(f"cp -r {self.fp} {new_path}")

    def update_parent_dir(self, new_path):
        self.fp = os.path.join(new_path, str(self.steamid))

    @classmethod
    def create_from_path(cls, filepath):
        try:
            tree = ET.parse(os.path.join(filepath, "About/About.xml"))
            root = tree.getroot()
            name = root.find("name").text
            author = root.find("author").text
            versions = [v.text for v in root.find("supportedVersions").findall("li")]
            try:
                with open(os.path.join(filepath, "About/PublishedFileId.txt")) as f:
                    steamid = f.readline().strip()
            except FileNotFoundError:
                steamid = None

            return Mod(name, steamid, versions, author, filepath)
        except (NotADirectoryError, FileNotFoundError) as e:
            print(os.path.basename(filepath) + " is not a mod. Ignoring.")
            return None


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
        return filter(None, [m.steamid for m in mods])


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

    def get_mods_as_list_both(self) -> list[Mod]:
        if (
            self.workshop_path
            and (workshop_mods := self.get_mods_as_list_workshop()) is not None
        ):
            return self.get_mods_as_list() + workshop_mods
        return self.get_mods_as_list()

    def get_mods_as_list_workshop(self) -> list[Mod]:
        return ModList.get_mods_list_by_path(self.workshop_path)

    def get_mods_as_list(self) -> list[Mod]:
        return ModList.get_mods_list_by_path(self.moddir)

    def get_mods_names(self) -> list[str]:
        return ModList.get_mods_list_names(self.get_mods_as_list_both())

    def backup_mod_dir(self, tarball_fp):
        query = '(cd {}; tar -vcaf "{}" ".")'.format(self.moddir, tarball_fp)
        for line in execute(query):
            print(line, end="")

    def sync_mod_list(self, mod_list: list[int]) -> bool:
        SteamDownloader().download(mod_list, self.cachedir)
        mods = ModList.get_mods_list_filter_by_id(self.cache_content_dir, mod_list)
        current_mods = self.get_mods_as_list()
        if self.workshop_path:
            workshop_mods = self.get_mods_as_list_workshop()
        for n in mods:
            install_path = self.moddir
            print(f"Installing {n.name}")
            if c := ModList.get_by_id(current_mods, n.steamid):
                c.remove()
            if self.workshop_path and (
                c := ModList.get_by_id(workshop_mods, n.steamid)
            ):
                c.remove()
                install_path = self.workshop_path

            if m := Mod.create_from_path(os.path.join(install_path, n.steamid)):
                print(f"Mod with missing PublishedIdFile.txt name space collision at: {m.fp}\nRemoving directory...")
                m.remove()

            n.install(install_path)

        return True

    def sync_mod(self, steamid: int) -> bool:
        return self.sync_mod_list([steamid])

    def sync_mod_list_file(self, modlist_fp):
        return self.sync_mod_list(ModListFile.read_text_modlist(modlist_fp))

    def update_all_mods(self):
        self.sync_mod_list(ModList.to_int_list(self.get_mods_as_list_both()))

    def remove_mod_list(self, modlist: list[Mod]) -> bool:
        for m in modlist:
            print("Removing {} by {}...".format(m.name, m.author))
            m.remove()
        return True

    def get_mod_table(self):
        import tabulate

        return tabulate.tabulate(
            [m.__cell__() for m in self.get_mods_as_list_both()],
            headers=["Name", "Author", "SteamID", "Versions"],
        )


class CLI:
    def __init__(self):
        parser = argparse.ArgumentParser(
            prog="rmm",
            description="Rimworld Mod Manager (RMM)",
            usage="""rmm <command> [<args>]
The available commands are:
    backup      Creates an archive of the package library
    export      Saves package library state to a file
    list        List installed packages
    remove      Removes a package or modlist
    search      Searches the workshop for mod
    sync        Installs a package or modlist
    update      Update all packages
    query       Search for a locally installed mod
    
""",
        )
        parser.add_argument("command", help="Subcommand to run")
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        args = parser.parse_args(sys.argv[1:2])

        try:
            self.path = os.path.expanduser(os.environ["RMM_PATH"])
        except KeyError as err:
            print("RimWorld mod directory not set.\n" "Trying default directories...")
            for path in DEFAULT_GAME_PATHS:
                p = os.path.expanduser((os.path.join(path, "game", "Mods")))
                if os.path.isdir(p):
                    self.path = p
        finally:
            if not hasattr(self, "path"):
                print(
                    "Game not found.\n"
                    'Please set "RMM_PATH" variable to the RimWorld mod directory in your environment.\n'
                    '\nexport RMM_PATH="~/games/rimworld"\nrmm list\n or \n'
                    'RMM_PATH="~/games/rimworld" rmm list'
                )
                exit(1)

        if not os.path.basename(self.path) == "Mods":
            for root, dirs, files in os.walk(self.path):
                if os.path.basename(root) == "game" and "Mods" in dirs:
                    # TODO read gameinfo file to ensure is actually rimworld
                    self.path = os.path.join(root, "Mods")
                    break

        print("rimworld path: {}".format(self.path))

        try:
            self.workshop_path = os.path.expanduser(os.environ["RMM_WORKSHOP_PATH"])
            if (
                not os.path.basename(self.workshop_path) == "294100"
                and "Steam" in self.workshop_path
            ):
                self.workshop_path = os.path.join(
                    "".join(self.workshop_path.partition("Steam/")[0:2]),
                    "steamapps/workshop/content/294100",
                )

            if not os.path.isdir(self.workshop_path):
                print(f"workshop path {self.workshop_path} not found. ignoring.")
                self.workshop_path = None

        except KeyError as err:
            if "/Steam/steamapps/common" in self.path:
                self.workshop_path = os.path.join(
                    "".join(self.path.partition("/Steam/steamapps")[0:2]),
                    "workshop/content/294100",
                )
            else:
                self.workshop_path = None

        if self.workshop_path:
            print(f"workshop path: {self.workshop_path}\n")

        if not hasattr(self, args.command):
            print("Unrecognized command")
            parser.print_help()
            exit(2)
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)()

    def search(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="searches the workshop for specified modname"
        )
        parser.add_argument("modname", help="name of mod", nargs="*")
        args = parser.parse_args(sys.argv[2:])
        search_term = " ".join(args.modname)
        results = WorkshopWebScraper.workshop_search(search_term)
        from tabulate import tabulate

        print(tabulate(reversed(results)))

    def export(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="Saves modlist to file."
        )
        parser.add_argument(
            "filename", help="filename to write modlist to or specify '-' for stdout"
        )
        args = parser.parse_args(sys.argv[2:])
        mods = Manager(self.path, self.workshop_path).get_mods_as_list_both()
        if args.filename != "-":
            ModListFile.write_text_modlist(mods, args.filename)
            print("Mod list written to {}.\n".format(args.filename))
        else:
            print(ModListFile.export_text_modlist(mods))

    def list(self):
        if not (s := Manager(self.path, self.workshop_path).get_mod_table()):
            print("No mods installed. Add them using the 'sync' command.")
        else:
            print(s)

    def install(self):
        self.sync()

    def sync(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="Syncs a mod from the workshop"
        )
        parser.add_argument("modname", help="mod or modlist to sync", nargs="*")
        parser.add_argument(
            "-f",
            "--file",
            action="store_true",
            help="specify modlist instead of modname",
        )
        args = parser.parse_args(sys.argv[2:])
        search_term = " ".join(args.modname)

        if args.file:
            Manager(self.path, self.workshop_path).sync_mod_list_file(search_term)

        if not args.file:
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

    def update(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="Updates all mods in directory"
        )
        parser.add_argument("filename", nargs="?", const=1, default=self.path)
        args = parser.parse_args(sys.argv[2:])

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

    def backup(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="Creates a backup of the mod directory state."
        )
        parser.add_argument(
            "filename", nargs="?", const=1, default="/tmp/rimworld.tar.bz2"
        )
        args = parser.parse_args(sys.argv[2:])

        print("Backing up mod directory to '{}.\n".format(args.filename))
        Manager(self.path, self.workshop_path).backup_mod_dir(args.filename)
        print("Backup completed to " + args.filename + ".")

    def remove(self):
        parser = argparse.ArgumentParser(prog="rmm", description="remove a mod")
        parser.add_argument("modname", help="name of mod", nargs="*")
        args = parser.parse_args(sys.argv[2:])
        search_term = " ".join(args.modname)
        search_result = [
            r
            for r in Manager(self.path, self.workshop_path).get_mods_as_list_both()
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

    def query(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="query locally installed mods"
        )
        parser.add_argument("modname", help="name of mod", nargs="*")
        args = parser.parse_args(sys.argv[2:])
        search_term = " ".join(args.modname)

        search_result = [
            r
            for r in Manager(self.path, self.workshop_path).get_mods_as_list_both()
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


def run():
    t = CLI()


if __name__ == "__main__":
    run()
