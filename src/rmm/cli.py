from __future__ import annotations

import importlib.metadata
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple, cast, Optional
from collections import namedtuple
from tabulate import tabulate

import util

from core import (
    Mod,
    ModFolder,
    ModList,
    ModListFile,
    ModListSerializer,
    ModListV2Format,
    PathFinder,
    SteamDownloader,
    WorkshopResult,
    WorkshopWebScraper,
    ModsConfig,
    EXPANSION_PACKAGE_ID,
)
from exception import InvalidSelectionException

USAGE = """
RimWorld Mod Manager

Usage:
rmm [options] config
rmm [options] export <file>
rmm [options] import <file>
rmm [options] list
rmm [options] query [<term>...]
rmm [options] remove [<term>...]
rmm search <term>...
rmm [options] sort
rmm [options] sync [sync options] <name>...
rmm [options] update [sync options]
rmm -h | --help
rmm -v | --version

Operations:
config            Sort and enable/disable mods
export            Save mod list to file.
import            Install a mod list from a file.
list              List installed mods.
query             Search installed mods.
remove            Remove installed mod.
search            Search Workshop.
sort              Auto-sort your modslist
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

class ModQueue(NamedTuple):
    packageid: str|None
    steamid: int|None
    name: str|None
    author: str|None

    def title(self):
        return self.packageid if self.packageid else f"{self.name} by {self.author}"


class Config:
    def __init__(
            self, path: Optional[Path] = None, workshop_path: Optional[Path] = None, config_path: Optional[Path] = None
    ):
        self.path = cast(Path, path)
        self.workshop_path = workshop_path
        self.config_path = config_path


def expand_ranges(s: str) -> str:
    return re.sub(
        r"(\d+)-(\d+)",
        lambda match: " ".join(
            str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)
        ),
        s,
    ).replace(",", " ")

def install_mod(path, config, steamid: int):
    if not steamid:
        raise Exception("Missing SteamID")
    util.copy(
        path / str(steamid),
        config.path / str(steamid),
        recursive=True,
    )
    return True

def create_mod_queue(mod_install_queue: list[Mod]|list[WorkshopResult]):
    queue = set()
    for n in mod_install_queue:
        if isinstance(n, WorkshopResult):
            queue.add(ModQueue(None, n.steamid, n.name, n.author))
        elif isinstance(n, Mod):
            queue.add(ModQueue(n.packageid, n.steamid, n.name, n.author))
    return queue

def remove_mod(mod: ModQueue, config: Config):
    game_dir_mods = ModFolder.create_mods_list(config.path)

    print(f"Uninstalling {mod.title()}")
    util.remove((config.path / str(mod.steamid)))


def remove_mods(mod_install_queue: list[Mod]|list[WorkshopResult], config: Config):
    queue = create_mod_queue(mod_install_queue)
    for mod in queue:
        remove_mod(mod, config)


def sync_mods(mod_install_queue: list[Mod]|list[WorkshopResult], config: Config):
    (cache_mods, steam_cache_path) = SteamDownloader.download([ mod.steamid for mod in mod_install_queue if mod.steamid ])
    game_dir_mods = ModFolder.create_mods_list(config.path)

    queue = create_mod_queue(mod_install_queue)

    for mod in queue:
        success = False
        try_install = False
        try:
            success = install_mod(steam_cache_path, config, mod.steamid)
        except FileExistsError:
            try_install = True
            remove_mod(mod, config)
        except FileNotFoundError:
            print(f"Unable to download and install {mod.title()}\n\tDoes this mod still exist?")
        finally:
            if try_install:
                success = install_mod(steam_cache_path, config, mod.steamid)
        if success:
            print(f"Installed {mod.title()}")


def tabulate_mod_or_wr(mods: ModList|list[WorkshopResult], numbered=False, reverse=False, alpha=False) -> str:
    if not mods:
        return None
    mod_list = [[n.name, n.author[:20]] for n in mods]
    headers=["name", "author"]
    if numbered:
        headers=["no", "name", "author"],
        new_list = []
        offset = 0
        if not reverse:
            offset = len(mod_list) + 1
        for k,v in enumerate(mod_list):
            new_list.append([abs(k+1 - offset), v[0], v[1]])

        mod_list = new_list
    if alpha:
        mod_list = sorted(mod_list)
    if reverse:
        mod_list = reversed(mod_list)

    return tabulate(
        mod_list,
        headers=headers,
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
    print(tabulate_mod_or_wr(ModFolder.create_mods_list(config.path)))


def query(args: list[str], config: Config):
    search_term = " ".join(args[1:])
    print(tabulate_mod_or_wr(ModFolder.search(config.path, search_term)))


def search(args: list[str], config: Config):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)
    print(tabulate([[r.name, r.author, r.num_ratings, r.description] for r in results]))


def capture_range(length: int):
    if length == 0:
        return None
    while True:
        try:
            selection = input()
            selection = [length - int(s) + 1 for s in expand_ranges(selection).split(" ")]
            for n in selection:
                if n > length or n <= 0:
                    raise InvalidSelectionException("Out of bounds")
            break
        except ValueError:
            print("Must enter valid integer or range")
        except InvalidSelectionException:
            print("Selection out of bounds.")

    return selection

def sync(args: list[str], config: Config):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)

    print(tabulate_mod_or_wr(results, numbered=True))

    print("Packages to install (eg: 2 or 1-3)")
    selection = capture_range(len(results))
    if not selection:
        exit(0)
    queue = list( reversed([results[m - 1] for m in selection]) )
    print(
        "Package(s): \n{} \n\nwill be installed. Continue? [y/n] ".format("  \n".join([f"{m.name} by {m.author}" for m in queue])),
        end="",
    )

    sync_mods(queue, config)


def remove(args: list[str], config: Config):
    search_term = " ".join(args[1:])
    search_result = ModFolder.search(config.path, search_term)

    if not search_result:
        print(f"No packages matching {search_term}")
        return False

    print(tabulate_mod_or_wr(search_result, reverse=True, numbered=True))
    print("Packages to remove (eg: 1 2 3 or 1-3)")

    selection = capture_range(len(search_result))

    remove_queue = [search_result[m - 1] for m in selection]
    print("Would you like to remove? ")

    for m in remove_queue:
        print("{} by {}".format(m.name, m.author))

    print("[y/n]: ", end="")

    if input() != "y":
        return False

    remove_mods(remove_queue, config)


def config(args: list[str], config: Config):
    game_mod_config = ModsConfig(
        PathFinder.find_config_defaults() / "Config/ModsConfig.xml"
    )
    installed_mods = ModFolder.create_mods_list(config.path)
    enabled_mods = game_mod_config.mods

    mod_state = []
    for n in enabled_mods:
        if n in installed_mods + EXPANSION_PACKAGE_ID:
            mod_state.append((n.packageid.lower(), True))

    for n in installed_mods:
        if n not in enabled_mods:
            mod_state.append((n.packageid.lower(), False))

    import multiselect, curses

    mod_state = curses.wrapper(multiselect.multiselect_order_menu, mod_state)

    new_mod_order = []
    for n in mod_state:
        if n[1] == True:
            new_mod_order.append(Mod(n[0]))
    game_mod_config.mods = new_mod_order
    game_mod_config.write()


def sort(args: list[str], config: Config):
    # TODO: fix this
    game_mod_config = ModsConfig(
        PathFinder.find_config_defaults() / "Config/ModsConfig.xml"
    )
    installed_mods = ModFolder.create_mods_list(config.path)

    game_mod_config.autosort(installed_mods, config)
    game_mod_config.write()


def update(args: list[str], config: Config):
    mods = ModFolder.create_mods_list(config.path)
    mods = [ m for m in mods if m.steamid]
    mod_names = "\n  ".join([n.name for n in mods])
    print("Preparing to update following packages:")
    print(mod_names)
    print(
        "\nThe action will overwrite any changes to the mod directory\n"
        "Add a .rmm_ignore to your mod directory to exclude it frome this list.\n"
        "Would you like to continue? [y/n]"
    )

    if input() != "y":
        return False

    sync_mods(mods, config)


def export(args: list[str], config: Config):
    mods = ModFolder.create_mods_list(config.path)
    joined_args = " ".join(args[1:])
    ModListFile.write(Path(joined_args), mods, ModListV2Format())
    print(f"Mod list written to {joined_args}")


def _import(args: list[str], config: Config):
    joined_args = " ".join(args[1:])
    mod_install_queue = ModListFile.read(Path(joined_args))

    if not mod_install_queue:
        print("No mods imported")
        exit(1)

    mod_install_queue = [ n for n in mod_install_queue if n.steamid ]

    unknown = 0
    for mod in mod_install_queue:
        display = ""
        if mod.name:
            display += mod.name
            if mod.author:
                display += f" by { mod.author }"
        elif mod.packageid:
            display = mod.packageid
        else:
            unknown += 1
        if display:
            print(display)

    print("\nImport package(s)? [y/n]:")

    if input() != "y":
        return False


    sync_mods(mod_install_queue, config)

def run():
    config = parse_options()
    if config.path:
        config.path = PathFinder.find_game(config.path)
    if not config.path:
        try:
            config.path = PathFinder.find_game(Path(os.environ["RMM_PATH"]))
        except KeyError:
            config.path = PathFinder.find_game_defaults()

    if not config.path:
        print(
            "\nUnable to find rimworld path.\nPlease set RMM_PATH environment variable to your mods folder.\nAlternative, use the -p directive: 'rmm -p game_path list'."
        )
        exit(1)

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
        "config",
        "sort",
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

    if sys.argv:
        command = get_long_name_from_alias_map(sys.argv[0], actions)
        if command and command in globals():
            globals()[command](sys.argv, config)
            sys.exit(0)

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
    # test.remove_mod(Mod('jaxe.rimhud'))
    # test.write()

    # ModListFile.write(Path("/tmp/test_modlist"), mods, ModListV1Format())
    # print(len(ModListFile.read(Path("/tmp/test_modlist"), ModListV1Format())))

    # results = list(WorkshopWebScraper.search("rimhud"))
    # for n in range(1):
    #     print(results[n].get_details())
    #     print()
