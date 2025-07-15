import argparse
from pathlib import Path
from .manager import Manager
from rmm import Config
from rmm import ModInstaller
from rmm import ModLister


def create_parser():
    parser = argparse.ArgumentParser(description="RimWorld Mod Manager")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Common arguments
    parser.add_argument("-p", "--path", type=str, help="RimWorld path.")
    parser.add_argument("-c", "--config", type=str, help="User config path.")
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create a configuration file at ~/.config/rrm",
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
    subparsers.add_parser("update", help="Update all mods from Steam.")

    return parser


def run():
    parser = create_parser()
    args = parser.parse_args()

    if args.create:
        if not args.path:
            print("Must pass -p RimWorld/Game/Path")
            return 1
        Config(args.path).save_config()
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

    # Handle the install command
    if args.command == "install":
        mod_installer = ModInstaller(
            steamcmd_path=Path("path/to/steamcmd"), mod_install_path=config.mod_path
        )
        mod_installer.install_mod(args.name)

    if args.command == "list":
        mod_lister = ModLister(manager)
        mod_lister.display_mods()


if __name__ == "__main__":
    run()
