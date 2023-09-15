from __future__ import annotations

import importlib.metadata
import os
import re
import sys
from pathlib import Path
from typing import cast

from tabulate import tabulate

from . import util
from .config import Config
from .exception import InvalidSelectionException
from .manager import Manager
from .mod import Mod
from .modlist import ModListFile, ModListV2Format
from .path import PathFinder
from .steam import WorkshopResult, WorkshopWebScraper

USAGE = """
RimWorld Mod Manager

Usage:
rmm [options] config
rmm [options] export [-e]|[-d] <file>
rmm [options] import <file>
rmm [options] enable [-a]|[-f file]|<packageid>|<term>
rmm [options] disable [-a]|[-f file]|<packageid>|<term>
rmm [options] remove [-a]|[-f file]|<packageid>|<term>
rmm [options] list
rmm [options] query [<term>]
rmm [options] search <term>
rmm [options] sort
rmm [options] sync <name>
rmm [options] update
rmm [options] verify

rmm -h | --help
rmm -v | --version

Operations:
config            Sort and enable/disable mods with ncurses
export            Save mod list to file.
import            Install a mod list from a file.
list              List installed mods.
query             Search installed mods.
remove            Remove installed mod.
search            Search Workshop.
sort              Auto-sort your modlist
sync              Install or update a mod.
update            Update all mods from Steam.
verify            Checks that enabled mods are compatible
enable            Enable mods
disable           Disable mods
order             Lists mod order

Parameters
term              Name, author, steamid
file              File path for a mod list
name              Name of mod.

Flags
-a                Performs operation on all mods
-d                Export disabled mods to modlist.
-e                Export enabled mods to modlist.
-f                Specify mods in a mod list

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

Tip:
You can use enable, disable, and remove with no
argument to select from all mods.
"""


def mods_config_dec(func):
    def wrapper_func(*args, **kwargs):
        try:
            args[1].modsconfig
        except AttributeError:
            print(
                "Please specify your RimWorld config directory with -u\n"
                "If you have not yet, start your game to create this directory."
            )
            exit(0)
        func(*args, **kwargs)

    return wrapper_func


def _interactive_query(manager: Manager, term: str, verb: str):
    search_result = manager.search_installed(term)
    if not search_result:
        print(f"No packages matching {search_term}")
        return False

    print(tabulate_mod_or_wr(search_result, reverse=True, numbered=True))
    print(f"Packages to {verb} (eg: 1,3,5-9)")

    selection = capture_range(len(search_result))
    for n in selection:
        print(n)
    if selection:
        return [search_result[m - 1] for m in selection]
    else:
        print("No selection made.")
        return None


def _interactive_verify(mods: list[Mod], verb: str):
    for m in mods:
        print(m.title())

    print(f"Proceed with {verb}? ", end="")
    print("[y/n]: ", end="")

    if input() != "y":
        return False
    return True


def _cli_parse_modlist(args):
    modlist_filename = args[2]
    modlist_path = Path(modlist_filename)
    queue = ModListFile.read(modlist_path)
    return queue


def _interactive_selection(args: list[str], manager: Manager, verb: str, f):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")

    queue = None
    if len(args) == 1:
        pass
    elif args[1] == "-f":
        print(args[2])
        queue = _cli_parse_modlist(args)
        args = args[2:]

    elif args[1] == "-a":
        queue = manager.installed_mods()

    if not queue:
        search_term = " ".join(args[1:])
        queue = _interactive_query(manager, search_term, verb)

    if not queue:
        exit(0)
    _interactive_verify(queue, verb)
    f(queue)


def _expand_ranges(s: str) -> str:
    return re.sub(
        r"(\d+)-(\d+)",
        lambda match: " ".join(
            str(i) for i in range(int(match.group(1)), int(match.group(2)) + 1)
        ),
        s,
    ).replace(",", " ")


def tabulate_mod_or_wr(
    mods,
    numbered=False,
    reverse=False,
    alpha=False,
    reversed_numbering=True,
    light=False,
) -> str:
    if not mods:
        return ""
    if isinstance(mods, dict):
        mods = [n for _, n in mods.items()]

    if isinstance(mods[0], Mod):
        headers = ["package", "name", "author", "enabled"]
        mod_list = [[n.packageid, n.name, n.author[:20], n.enabled] for n in mods]
    elif isinstance(mods[0], WorkshopResult) or light:
        headers = ["name", "author"]
        mod_list = [[n.name, n.author[:20]] for n in mods]
    else:
        return None

    if numbered:
        headers = ["no"] + headers
        new_list = []
        offset = 0
        if not reverse:
            offset = len(mod_list) + 1
        if reversed_numbering:
            for k, v in enumerate(mod_list):
                new_list.append([abs(k + 1 - offset), *v])
        else:
            for k, v in enumerate(mod_list):
                new_list.append([k + 1, *v])

        mod_list = new_list
    if alpha:
        mod_list = sorted(mod_list)
    if reverse:
        mod_list = reversed(mod_list)

    return tabulate(
        mod_list,
        headers=headers,
    )


def _get_long_name_from_alias_map(word, _list):
    for item in _list:
        if isinstance(item, tuple):
            if word in list(item):
                return item[0]
        if isinstance(item, str):
            if word == item:
                return word
    return None


def help(args: list[str], manager: Manager):
    print(USAGE)


def version(args: list[str], manager: Manager):
    try:
        print(importlib.metadata.version("rmm-spoons"))
    except importlib.metadata.PackageNotFoundError:
        print("version unknown")


@mods_config_dec
def _list(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    print(tabulate_mod_or_wr(manager.installed_mods(), alpha=True))


@mods_config_dec
def query(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    search_term = " ".join(args[1:])
    print(tabulate_mod_or_wr(manager.search_installed(search_term), alpha=True))


def search(args: list[str], manager: Manager):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args, reverse=True)
    print(tabulate_mod_or_wr(results))


def capture_range(length: int):
    if length == 0:
        return None
    while True:
        try:
            strInput = input()
            selection = capture_indexes(strInput)
            for n in selection:
                if n > length or n <= 0:
                    raise InvalidSelectionException("Out of bounds")
            break
        except ValueError:
            print("Must enter valid integer or range")
        except InvalidSelectionException:
            print("Selection out of bounds.")

    return selection


# get mod index from input by space separated list of numbers or ranges like 1-3
def capture_indexes(strInput: str):
    if not strInput:
        return None
    selection = []
    for s in strInput.split(" "):
        if "-" in s:
            start, end = s.split("-")
            selection.extend(range(int(start), int(end) + 1))
        else:
            selection.append(int(s))
    return selection


@mods_config_dec
def sync(args: list[str], manager: Manager):
    joined_args = " ".join(args[1:])
    results = WorkshopWebScraper.search(joined_args)
    print(
        tabulate_mod_or_wr(
            results, numbered=True, reverse=True, reversed_numbering=True
        )
    )
    print("Packages to install (eg: 2 or 1-3)")
    selection = capture_range(len(results))
    if not selection:
        exit(0)
    queue = list(reversed([results[m - 1] for m in selection]))
    print(
        "Package(s): \n{} \n\nwill be installed.".format(
            "  \n".join([f"{m.name} by {m.author}" for m in queue])
        ),
        end="",
    )
    print()

    manager.sync_mods(queue)


def remove(args: list[str], manager: Manager):
    _interactive_selection(args, manager, "remove", manager.remove_mods)


@mods_config_dec
def enable(args: list[str], manager: Manager):
    _interactive_selection(args, manager, "enable", manager.enable_mods)
    print("\nRecommend to use auto sort")


@mods_config_dec
def disable(args: list[str], manager: Manager):
    _interactive_selection(args, manager, "disable", manager.disable_mods)
    print("\nRecommend to use auto sort")


@mods_config_dec
def config(args: list[str], manager: Manager):
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    if not manager.config.modsconfig_path:
        raise Exception("ModsConfig.xml not found")

    import curses

    import rmm.multiselect as multiselect

    data = manager.order_all_mods()
    mod_state = curses.wrapper(multiselect.multiselect_order_menu, data)
    new_mod_order = [k for k, v in mod_state if v == True]

    manager.modsconfig.mods = new_mod_order
    manager.modsconfig.write()


@mods_config_dec
def sort(args: list[str], manager: Manager):
    # print(manager.config.config_path)
    if not manager.config.mod_path:
        raise Exception("Game path not defined")
    if not manager.config.modsconfig_path:
        raise Exception("ModsConfig.xml not found")

    manager.modsconfig.autosort(manager.installed_mods(), manager.config)
    manager.modsconfig.write()


@mods_config_dec
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


@mods_config_dec
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


@mods_config_dec
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


@mods_config_dec
def order(args: list[str], manager: Manager):
    print(
        tabulate_mod_or_wr(
            manager.order_mods(),
            numbered=True,
            reverse=False,
            reversed_numbering=False,
        )
    )


def verify(args: list[str], manager: Manager):
    print(manager.verify_mods())


def windows_setup():
    try:
        if not util.platform() == "win32":
            pass
        substring = "site-packages\\rmm"
        string = os.path.realpath(__file__)
        if substring in string:
            string = str(Path(string.split("site-packages\\rmm")[0]) / "Scripts")
            if string not in os.environ["PATH"]:
                print(
                    f'You should add "{string}" to your PATH variable so you can directly access the rmm command.'
                )
    except AttributeError:
        pass


def parse_options() -> Config:
    path_options = [
        ("mod_path", "--path", "-p"),
        ("workshop_path", "--workshop", "-w"),
        ("config_path", "--user", "-u"),
    ]

    config = Config()
    del sys.argv[0]
    try:
        while s := _get_long_name_from_alias_map(
            sys.argv[0], [p for p in path_options]
        ):
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


def run():
    windows_setup()
    config = parse_options()
    if config.mod_path:
        config.mod_path = PathFinder.find_game(config.mod_path)
    if not config.mod_path:
        try:
            config.mod_path = PathFinder.find_game(
                Path(util.sanitize_path(os.environ["RMM_PATH"]))
            )
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
        config.config_path = PathFinder.find_config(config.config_path)

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
        "verify",
        "enable",
        "disable",
        "order",
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
        command = _get_long_name_from_alias_map(sys.argv[0], actions)
        if command and command in globals():
            globals()[command](sys.argv, manager)
            windows_setup()
            sys.exit(0)

    print(USAGE)
    # windows_setup()
    sys.exit(0)


if __name__ == "__main__":
    run()
