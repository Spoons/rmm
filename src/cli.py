from __future__ import annotations

import importlib.metadata
import os
import re
import sys
from pathlib import Path
from typing import Optional, cast

from tabulate import tabulate

import rmm.util as util
from rmm.config import Config
from rmm.exception import InvalidSelectionException
from rmm.manager import Manager
from rmm.mod import EXPANSION_PACKAGES, Mod
from rmm.modlist import ModListFile, ModListV2Format
from rmm.path import PathFinder
from rmm.steam import WorkshopResult, WorkshopWebScraper

USAGE = """
RimWorld Mod Manager

Usage:
rmm [options] config
rmm [options] export [-e]|[-d] <file>
rmm [options] import <file>
rmm [options] list
rmm [options] query [<term>...]
rmm [options] remove [-f file]|[<term>...]
rmm [options] search <term>...
rmm [options] sort
rmm [options] sync <name>...
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

Export Option:
-d                Export disabled mods to modlist.
-e                Export enabled mods to modlist.

Remove Options:
-f                Remove mods listed in modlist.

Options:
-p --path DIR     RimWorld path.
-w --workshop DIR Workshop Path.
-u --user DIR     User config path.

Environment Variables:
RMM_PATH          Folder containings Mods
RMM_WORKSHOP_PATH Folder containing Workshop mods (optional)
RMM_USER_PATH     Folder containing saves and config

Pathing Preference:
CLI Argument > Environment Variable > Defaults
"""


def expand_ranges(s: str) -> str:
    return re.sub(
        r"(\d+)-(\d+)",
        lambda match: " ".join(
            str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)
        ),
        s,
    ).replace(",", " ")


def tabulate_mod_or_wr(
    mods: Optional[list[WorkshopResult] | list[Mod]],
    numbered=False,
    reverse=False,
    alpha=False,
) -> str:
    if not mods:
        return ""
    mod_list = [[n.name, n.author[:20]] for n in mods if n.name and n.author]
    headers = ["name", "author"]
    if numbered:
        headers = ["no", "name", "author"]
        new_list = []
        offset = 0
        if not reverse:
            offset = len(mod_list) + 1
        for k, v in enumerate(mod_list):
            new_list.append([abs(k + 1 - offset), v[0], v[1]])

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
    path_options = [
        ("mod_path", "--path", "-p"),
        ("workshop_path", "--workshop", "-w"),
        ("config_path", "--user", "-u"),
    ]

    config = Config()
    del sys.argv[0]
    try:
        while s := get_long_name_from_alias_map(sys.argv[0], [p for p in path_options]):
            del sys.argv[0]
            print(sys.argv[0])
            path_str = sys.argv[0]
            if util.platform() == "win32":
                path = Path(str(path_str).strip('"'))
            else:
                path = Path(path_str)
            setattr(config, s, path)
            del sys.argv[0]

    except IndexError:
        pass

    return config


def help(args: list[str], manager: Manager):
    print(USAGE)


def version(args: list[str], manager: Manager):
    try:
        print(importlib.metadata.version("rmm-spoons"))
    except importlib.metadata.PackageNotFoundError:
        print("version unknown")


def _list(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    print(tabulate_mod_or_wr(manager.installed_mods()))


def query(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    search_term = " ".join(args[1:])
    print(tabulate_mod_or_wr(manager.search_installed(search_term)))


def search(args: list[str], manager: Manager):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)
    print(tabulate_mod_or_wr(results))


def capture_range(length: int):
    if length == 0:
        return None
    while True:
        try:
            selection = input()
            selection = [
                length - int(s) + 1 for s in expand_ranges(selection).split(" ")
            ]
            for n in selection:
                if n > length or n <= 0:
                    raise InvalidSelectionException("Out of bounds")
            break
        except ValueError:
            print("Must enter valid integer or range")
        except InvalidSelectionException:
            print("Selection out of bounds.")

    return selection


def sync(args: list[str], manager: Manager):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)
    print(tabulate_mod_or_wr(results, numbered=True))
    print("Packages to install (eg: 2 or 1-3)")
    selection = capture_range(len(results))
    if not selection:
        exit(0)
    queue = list(reversed([results[m - 1] for m in selection]))
    print(
        "Package(s): \n{} \n\nwill be installed. Continue? [y/n] ".format(
            "  \n".join([f"{m.name} by {m.author}" for m in queue])
        ),
        end="",
    )

    manager.sync_mods(queue)


def remove(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")

    remove_queue = None
    if args[1] == "-f":
        modlist_filename = args[2]
        args = args[2:]
        modlist_path = Path(modlist_filename)
        remove_queue = ModListFile.read(modlist_path)

    if not remove_queue:
        search_term = " ".join(args[1:])
        search_result = manager.search_installed(search_term)

        if not search_result:
            print(f"No packages matching {search_term}")
            return False

        print(tabulate_mod_or_wr(search_result, reverse=True, numbered=True))
        print("Packages to remove (eg: 1 2 3 or 1-3)")

        selection = capture_range(len(search_result))
        if selection:
            remove_queue = [search_result[m - 1] for m in selection]
        else:
            print("No selection made.")
            return

    print("Would you like to remove? ")

    for m in remove_queue:
        print(m.title())

    print("[y/n]: ", end="")

    if input() != "y":
        print("nah")
        return False

    manager.remove_mods(remove_queue)


def config(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    if not manager.config.modsconfig_path:
        raise Exception("ModsConfig.xml not found")
    installed_mods = manager.installed_mods()
    enabled_mods = manager.enabled_mods()

    mod_state = []
    for n in enabled_mods:
        if n in installed_mods + EXPANSION_PACKAGES:
            mod_state.append((n.packageid, True))

    for n in installed_mods:
        if n not in enabled_mods:
            mod_state.append((n.packageid, False))

    import curses
    import multiselect

    mod_state = curses.wrapper(multiselect.multiselect_order_menu, mod_state)

    new_mod_order = []
    for n in mod_state:
        if n[1] == True:
            new_mod_order.append(Mod(packageid=n[0]))
    manager.modsconfig.mods = new_mod_order
    manager.modsconfig.write()


def sort(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    if not manager.config.modsconfig_path:
        raise Exception("ModsConfig.xml not found")

    manager.modsconfig.autosort(manager.installed_mods(), manager.config)
    manager.modsconfig.write()


def update(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    installed_mods_names = "\n  ".join(
        [n.name for n in manager.installed_mods() if n.name]
    )
    print("Preparing to update following packages:")
    print(installed_mods_names)
    print(
        "\nThe action will overwrite any changes to the mod directory\n"
        "Add a .rmm_ignore to your mod directory to exclude it frome this list.\n"
        "Would you like to continue? [y/n]"
    )

    if input() != "y":
        return False

    manager.sync_mods(manager.installed_mods())


def export(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    if args[1] == "-e":
        args = args[1:]
        mods = manager.enabled_mods()
    elif args[1] == "-d":
        args = args[1:]
        mods = manager.disabled_mods()
    else:
        mods = manager.installed_mods()

    joined_args = " ".join(args[1:])
    ModListFile.write(Path(joined_args), mods, ModListV2Format())
    print(f"Mod list written to {joined_args}")


def _import(args: list[str], manager: Manager):
    joined_args = " ".join(args[1:])
    mod_install_queue = ModListFile.read(Path(joined_args))

    if not mod_install_queue:
        print("No mods imported")
        exit(1)

    mod_install_queue = [n for n in mod_install_queue if n.steamid]

    for mod in mod_install_queue:
        print(mod.title())

    print("\nImport package(s)? [y/n]:")

    if input() != "y":
        return False

    manager.sync_mods(mod_install_queue)


def windows_setup():
    if not util.platform() == "win32":
        return
    pass


def run():
    windows_setup()
    config = parse_options()
    if config.mod_path:
        config.mod_path = PathFinder.find_game(config.mod_path)
    if not config.mod_path:
        try:
            config.mod_path = PathFinder.find_game(Path(util.sanitize_path(os.environ["RMM_PATH"])))
        except KeyError:
            config.mod_path = PathFinder.find_game_defaults()

    if not config.mod_path:
        print(
            "\nUnable to find rimworld path.\nPlease set RMM_PATH environment variable to your mods folder.\nAlternative, use the -p directive: 'rmm -p game_path list'."
        )
        exit(1)

    if config.workshop_path:
        config.workshop_path = PathFinder.find_workshop(Path(config.workshop_path))

    if not config.workshop_path:
        try:
            config.workshop_path = PathFinder.find_workshop(
                util.sanitize_path(Path(os.environ["RMM_WORKSHOP_PATH"]))
            )
        except KeyError:
            if config.mod_path:
                config.workshop_path = PathFinder.get_workshop_from_game_path(
                    Path(config.mod_path)
                )
            else:
                config.workshop_path = PathFinder.find_workshop_defaults()

    if config.config_path:
        config.config_path = PathFinder.find_game(config.config_path)

    if not config.config_path:
        try:
            config.config_path = PathFinder.find_config(
                util.sanitize_path(Path(os.environ["RMM_CONFIG_PATH"]))
            )
        except KeyError:
            config.config_path = PathFinder.find_config_defaults()

    if config.config_path:
        config.config_path = cast(Path, config.config_path)
        config.modsconfig_path = Path(config.config_path / "Config/ModsConfig.xml")
        if config.modsconfig_path:
            config.modsconfig_path = cast(Path, config.modsconfig_path)

    manager = Manager(config)


    actions = [
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
            globals()[command](sys.argv, manager)
            sys.exit(0)

    print(USAGE)
    sys.exit(0)


if __name__ == "__main__":
    run()
