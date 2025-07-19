import argparse
from pathlib import Path

from rmm.logger import setup_logging
from rmm.mod_new.mod_searcher import ModSearcher
from rmm.steam.downloader import SteamDownloader
from .manager import Manager
from rmm import Config
from rmm import ModInstaller
from rmm import ModLister
from rmm import ModUpdater


def create_parser():
    parser = argparse.ArgumentParser(description="RimWorld Mod Manager")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Common arguments
    parser.add_argument("-c", "--config", type=str, help="User config path.")

    config_parser = subparsers.add_parser(
        "configuration", help="Manage user configuration"
    )
    config_parser.add_argument("-p", "--path", type=Path, help="RimWorld path.")
    config_parser.add_argument(
        "-d", "--steamcmd", type=Path, help="SteamCMD executable path"
    )

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove installed mod.")
    remove_parser.add_argument(
        "term", type=str, nargs="?", help="Name, author, steamid"
    )

    # List command
    subparsers.add_parser("list", help="List installed mods.")

    # Query command
    query_parser = subparsers.add_parser("query", help="Search installed mods.")
    query_parser.add_argument("term", type=str, nargs="?", help="Name, author, steamid")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search Workshop.")
    search_parser.add_argument("term", type=str, help="Search term")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install a mod.")
    install_parser.add_argument("name", type=str, help="Name of mod.")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update mods.")
    update_parser.add_argument("--id", type=int, default=None)

    return parser


def run():
    logger = setup_logging()
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "configuration":
        if not args.path:
            print("Must pass -p RimWorld/Game/Path")
            return 1
        if not args.steamcmd:
            print("Must pass -d path/to/steamcmd")
            return 1
        Config(args.path, args.steamcmd).save_config()
        return 0

    # Load configuration
    try:
        config = Config.load_config(args.config or "~/.config/rmm.toml")
    except FileNotFoundError:
        print("Config file not found. Please create one with '--create'")
        return 2

    if not config.mod_path:
        print(
            "\nUnable to find RimWorld path.\nPlease set RMM_PATH environment variable to your mods folder.\nAlternatively, use the -p directive: 'rmm -p game_path list'."
        )
        return 10

    manager = Manager(config)
    mod_lister = ModLister(manager)
    downloader = SteamDownloader(config.steamcmd)

    logger.debug(config.to_dict())
    # Handle the install command
    if args.command == "install":
        mod_installer = ModInstaller(config.mod_path, downloader)
        mod_installer.install_mod(args.name)

    if args.command == "list":
        mods = mod_lister.list_mods()
        for mod in mods:
            print(mod)

    if args.command == "search":
        mod_searcher = ModSearcher()
        mod_searcher.display_search(args.term)

    if args.command == "update":
        mod_updater = ModUpdater(config.mod_path, downloader)
        if not args.id:
            return mod_updater.update_all_mods(mod_lister.list_mods())

        mod = manager.find_one_mod(args.id)
        mod_updater.update_mod(mod)


if __name__ == "__main__":
    run()
