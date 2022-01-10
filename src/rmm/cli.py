from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path
from typing import cast, Optional

from tabulate import tabulate

import util

from core import (
    Mod,
    ModFolderReader,
    ModList,
    ModListFile,
    ModListSerializer,
    ModListV2Format,
    PathFinder,
    SteamDownloader,
    WorkshopWebScraper,
)
from exception import InvalidSelectionException

USAGE = """
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


class Config:
    def __init__(
        self, path: Optional[Path] = None, workshop_path: Optional[Path] = None
    ):
        self.path = cast(Path, path)
        self.workshop_path = workshop_path


def tabulate_mods(mods: ModList) -> str:
    return tabulate(
        [[n.name, n.author[:20], n.steamid, n.ignored, n.path.name] for n in mods],
        headers=["name", "author", "steamid", "ignored", "folder"],
    )


def get_long_name_from_alias_map(word, _list):
    for item in _list:
        if isinstance(item, tuple):
            if word in list(item):
                return item[0]
        if isinstance(item, str):
            if word == item:
                return word
    return None


def parse_options() -> Config:
    path_options = [("path", "--path", "-p"), ("workshop_path", "--workshop", "-w")]

    config = Config()
    del sys.argv[0]
    try:
        while s := get_long_name_from_alias_map(sys.argv[0], [p for p in path_options]):
            del sys.argv[0]
            setattr(config, s, Path(sys.argv[0]))
            del sys.argv[0]
    except IndexError:
        pass

    return config


def help(args: list[str], config: Config):
    print(USAGE)


def version(args: list[str], config: Config):
    try:
        print(importlib.metadata.version("rmm-spoons"))
    except importlib.metadata.PackageNotFoundError:
        print("version unknown")


def _list(args: list[str], config: Config):
    print(tabulate_mods(ModFolderReader.create_mods_list(config.path)))


def query(args: list[str], config: Config):
    search_term = " ".join(args[1:])
    print(
        tabulate_mods(
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


def search(args: list[str], config: Config):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)
    print(tabulate([[r.name, r.author, r.num_ratings, r.description] for r in results]))


def sync(args: list[str], config: Config):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)
    print(
        tabulate(
            [
                [len(results) - k, r.name, r.author, r.num_ratings, r.description]
                for k, r in enumerate(results)
            ]
        )
    )
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

    selected = results[selection]
    print(
        "Package(s): {} will be installed. Continue? [y/n] ".format(selected.name),
        end="",
    )

    if input() != "y":
        return False

    (mods, path) = SteamDownloader.download([selected.steamid])
    mods_folder = ModFolderReader.create_mods_list(config.path)
    matched = cast(list[Mod], [n for n in mods_folder if n == selected.steamid])
    for n in matched:
        print(f"Uninstalling {n.packageid}")
        if n.path:
            util.remove(n.path)
        else:
            print(f"Could not remove: {n.packageid}")

    print(f"Installing {selected.name} by {selected.author}")
    print(path / str(selected.steamid))
    print(config.path)
    util.copy(
        path / str(selected.steamid),
        config.path / str(selected.steamid),
        recursive=True,
    )


def remove(args: list[str], config: Config):
    search_term = " ".join(args[1:])
    search_result = ModList(
        [
            r
            for r in ModFolderReader.create_mods_list(config.path)
            if str.lower(search_term) in str.lower(r.name)
            or str.lower(search_term) in str.lower(r.author)
            or search_term == r.steamid
        ]
    )

    if not search_result:
        print(f"No packages matching {search_term}")
        return False

    for n, element in enumerate(reversed(search_result)):
        n = abs(n - len(search_result))
        print("{}. {} by {}".format(n, element.name, element.author))
    print("Packages to remove (eg: 1 2 3 or 1-3)")

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

    # (mods, path) = SteamDownloader.download([n.steamid for n in remove_queue])
    mods_folder = ModFolderReader.create_mods_list(config.path)
    matched = cast(list[Mod], [n for n in mods_folder if n in remove_queue])
    for n in matched:
        print(f"Uninstalling {n.packageid}")


def update(args: list[str], config: Config):
    mods = ModFolderReader.create_mods_list(config.path)
    mod_names = "\n  ".join([n.name for n in mods])
    print("Preparing to update following packages:")
    print(mod_names)
    print(
        "\nThe action will overwrite any changes to the mod directory\n"
        "Add a .rmm_ignore to your mod directory to exclude it frome this list.\n"
        "Would you like to continue? [y/n]"
    )

    # if input() != "y":
    #     return False

    (_, path) = SteamDownloader.download([m.steamid for m in mods])

    for m in mods:
        print(f"Uninstalling {m.packageid}")
        if m.path:
            util.remove(m.path)
            print(f"Installing {m.packageid}")
            util.copy(
                path / str(m.steamid),
                config.path / str(m.steamid),
                recursive=True,
            )
        else:
            print(f"Could not remove: {m.packageid}")


def export(args: list[str], config: Config):
    mods = ModFolderReader.create_mods_list(config.path)
    joined_args = " ".join(args[1:])
    ModListFile.write(Path(joined_args), mods, ModListV2Format())
    print(f"Mod list written to {joined_args}")


def _import(args: list[str], config: Config):
    joined_args = " ".join(args[1:])
    mods = ModListFile.read(Path(joined_args))

    if not mods:
        print("No mods imported")
        exit(1)

    mods = cast(list[Mod], mods)

    unknown = 0
    for n in mods:
        display = ""
        if n.name:
            display += n.name
            if n.author:
                display += f" by { n.author }"
        elif n.packageid:
            display = n.packageid
        else:
            unknown += 1
        if display:
            print(display)

    print("\nImport package(s)? [y/n]:")

    if input() != "y":
        return False

    (cache_mods, path) = SteamDownloader.download([n.steamid for n in mods])
    game_mods = ModFolderReader.create_mods_list(config.path)
    matched = []
    for m in game_mods:
        if m in mods:
            matched.append(m)
    for n in matched:
        print(f"Uninstalling {n.packageid}")
        if n.path:
            util.remove(n.path)
        else:
            print(f"Could not remove: {n.packageid}")

    for n in mods:
        print(f"Installing {n.packageid}")
        util.copy(
            path / str(n.steamid),
            config.path / str(n.steamid),
            recursive=True,
        )


def run():
    config = parse_options()
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
        ("_import", "import"),
        ("_list", "list", "-Q"),
        ("query", "-Qs"),
        ("remove", "-R"),
        ("search", "-Ss"),
        ("sync", "-S"),
        ("update", "-Su"),
        ("help", "-h"),
        ("version", "-v"),
    ]

    command = get_long_name_from_alias_map(sys.argv[0], actions)
    if command and command in globals():
        globals()[command](sys.argv, config)
    else:
        print(USAGE)
        sys.exit(0)


if __name__ == "__main__":
    run()

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

    # ModListFile.write(Path("/tmp/test_modlist"), mods, ModListV1Format())
    # print(len(ModListFile.read(Path("/tmp/test_modlist"), ModListV1Format())))

    # results = list(WorkshopWebScraper.search("rimhud"))
    # for n in range(1):
    #     print(results[n].get_details())
    #     print()
