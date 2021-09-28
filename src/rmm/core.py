#!/usr/bin/env python3
import os
import sys
import xml.etree.ElementTree as ET
import requests as req
import shutil
import argparse
from enum import Enum
from bs4 import BeautifulSoup
from rmm.utils.processes import execute


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
        shutil.rmtree(self.fp)

    def install(self, moddir):
        new_path = moddir + "/" + str(self.steamid)
        shutil.copytree(self.fp, new_path, dirs_exist_ok=True)

    def update_parent_dir(self, new_path):
        self.fp = new_path + "/" + str(self.steamid)

    @classmethod
    def create_from_path(cls, filepath):
        try:
            tree = ET.parse(filepath + "/About/About.xml")
            root = tree.getroot()
            name = root.find("name").text
            author = root.find("author").text
            versions = [v.text for v in root.find("supportedVersions").findall("li")]
            with open(filepath + "/About/PublishedFileId.txt") as f:
                steamid = f.readline().strip()

            return Mod(name, steamid, versions, author, filepath)
        except NotADirectoryError:
            print(os.path.basename(filepath) + " is not a mod. Skipping.")


class ModList:
    @classmethod
    def read_text_modlist(cls, path):
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
    def export_text_modlist(cls, mods):
        output = ""
        for m in mods:
            output += "{}\n".format(m.steamid)
        return output

    @classmethod
    def write_text_modlist(cls, mods, path):
        with open(path, "w") as f:
            f.write(cls.export_text_modlist(mods))


class SteamDownloader:
    @classmethod
    def download(cls, mods, folder):
        def workshop_format(mods):
            return (s := " +workshop_download_item 294100 ") + s.join(
                str(x) for x in mods
            )

        query = 'steamcmd +login anonymous +force_install_dir "{}" "{}" +quit'.format(
            folder, workshop_format(mods)
        )

        for line in execute(query):
            print(line, end="")

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
    def __init__(self, moddir):
        self.moddir = moddir
        self.cachedir = "/tmp/rmm_cache"
        self.cache_content_dir = self.cachedir + "/steamapps/workshop/content/294100/"

    def get_mods_list(self) -> list[Mod]:
        return list(
            filter(
                None,
                [
                    Mod.create_from_path(self.moddir + "/" + d)
                    for d in os.listdir(self.moddir)
                ],
            )
        )

    def modlist_from_list_cache(self, mods):
        return [
            Mod.create_from_path(self.cache_content_dir + "/" + str(d)) for d in mods
        ]

    def get_mods_names(self):
        mods = self.get_mods_list()
        return [n.name for n in mods]

    def backup_mod_dir(self, tarball_fp):
        query = '(cd {}; tar -vcaf "{}" ".")'.format(self.moddir, tarball_fp)
        for line in execute(query):
            print(line, end="")

    def sync_mod(self, steamid):
        SteamDownloader().download([steamid], self.cachedir)
        print("\n\nsteamid: " + str(steamid) + "\n\n")
        mod = Mod.create_from_path(self.cache_content_dir + str(steamid))
        print(mod)
        mod.install(self.moddir)
        print("\nInstalled {}".format(mod.name))

    def sync_mod_list(self, modlist_fp):
        mods = ModList.read_text_modlist(modlist_fp)
        SteamDownloader().download(mods, self.cachedir)
        mods = self.modlist_from_list_cache(mods)
        print("\n")
        for n in mods:
            print("Installing {}".format(n.name))
            n.update_parent_dir(self.cache_content_dir)
            n.install(self.moddir)

    def update_all_mods(self, fp):
        mods = self.get_mods_list()
        SteamDownloader().download_modlist(mods, self.cachedir)
        print("\n")
        for n in mods:
            print("Updating {}".format(n.name))
            n.update_parent_dir(self.cache_content_dir)
            n.install(self.moddir)

    def remove_mod_list(self, modlist: list[Mod]) -> bool:
        for m in modlist:
            print("Removing {} by {}...".format(m.name, m.author))
            m.remove()
        return True

    def get_mod_table(self):
        from tabulate import tabulate

        return tabulate([m.__cell__() for m in self.get_mods_list()])


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
            self.path = os.environ["RMM_PATH"]
        except KeyError as err:
            print(
                "Rimworld mod directory not set.\n"
                'Please set "RMM_PATH" variable to the RimWorld mod directory in your environment.\n'
                '\nexport RMM_PATH="~/games/rimworld/game/Mods"\nrmm list\n or \n'
                'RMM_PATH="~/games/rimworld/game/Mods" rmm list'
            )
            exit(1)

        if not os.path.basename(self.path) == "Mods":
            print("This directory is not the 'Mods' directory. Scanning...")
            for root, dirs, files in os.walk(self.path):
                if os.path.basename(root) == "game" and "Mods" in dirs:
                    # TODO read gameinfo file to ensure is actually rimworld
                    self.path = root + "/" + "Mods"
                    break

            print("Found: {}\n".format(self.path))

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
        parser.add_argument("modname", help="name of mod")
        args = parser.parse_args(sys.argv[2:])
        results = WorkshopWebScraper.workshop_search(args.modname)
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
        mods = Manager(self.path).get_mods_list()
        if args.filename != "-":
            ModList.write_text_modlist(mods, args.filename)
            print("Mod list written to {}.\n".format(args.filename))
        else:
            print(ModList.export_text_modlist(mods))

    def list(self):
        if not (s := Manager(self.path).get_mod_table()):
            print("No mods installed. Add them using the 'sync' command.")
        print(s)

    def sync(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="Syncs a mod from the workshop"
        )
        parser.add_argument("modname", help="mod or modlist to sync")
        parser.add_argument(
            "-f",
            "--file",
            action="store_true",
            help="specify modlist instead of modname",
        )
        args = parser.parse_args(sys.argv[2:])

        if args.file:
            Manager(self.path).sync_mod_list(args.modname)

        if not args.file:
            results = WorkshopWebScraper.workshop_search(args.modname)
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

            Manager(self.path).sync_mod(
                results[selection][WorkshopResultsEnum.STEAMID.value]
            )

    def update(self):
        parser = argparse.ArgumentParser(
            prog="rmm", description="Updates all mods in directory"
        )
        parser.add_argument("filename", nargs="?", const=1, default=self.path)
        args = parser.parse_args(sys.argv[2:])

        print(
            "Preparing to update following packages: "
            + ", ".join(str(x) for x in Manager(self.path).get_mods_names())
            + "\n\nWould you like to continue? [y/n]"
        )

        if input() != "y":
            return False

        Manager(self.path).update_all_mods(args.filename)
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
        Manager(self.path).backup_mod_dir(args.filename)
        print("Backup completed to " + args.filename + ".")

    def remove(self):
        parser = argparse.ArgumentParser(prog="rmm", description="remove a mod")
        parser.add_argument("modname", help="name of mod")
        args = parser.parse_args(sys.argv[2:])

        search_result = [
            r
            for r in Manager(self.path).get_mods_list()
            if str.lower(args.modname) in str.lower(r.name)
            or str.lower(args.modname) in str.lower(r.author)
            or args.modname in r.steamid
        ]
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

        Manager(self.path).remove_mod_list(remove_queue)

    def query(self):
        parser = argparse.ArgumentParser(prog="rmm", description="query locally installed mods")
        parser.add_argument("modname", help="name of mod")
        args = parser.parse_args(sys.argv[2:])

        search_result = [
            r
            for r in Manager(self.path).get_mods_list()
            if str.lower(args.modname) in str.lower(r.name)
            or str.lower(args.modname) in str.lower(r.author)
            or args.modname in r.steamid
        ]
        print("Found: ")
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
