from typing_extensions import TypedDict
import tomli
import tomli_w
from pathlib import Path

DEFAULT_CONFIG_FILE: str = "~/.config/rmm.toml"


class ConfigPrimitives(TypedDict):
    mod_path: str
    config_path: str
    steamcmd: str


class Config:
    @classmethod
    def from_dict(cls, primitives: ConfigPrimitives):
        config = cls(
            mod_path=Path(primitives["mod_path"]),
            steamcmd=Path(primitives["steamcmd"]),
            config_path=Path(primitives["config_path"]),
        )
        return config

    @classmethod
    def load_config(cls, file_path: str = DEFAULT_CONFIG_FILE):
        with open(Path(file_path).expanduser(), "rb") as file:
            config_dict = tomli.load(file)
        return Config.from_dict(config_dict)  # type: ignore

    def __init__(
        self,
        mod_path: Path,
        steamcmd: Path,
        config_path: Path = Path(DEFAULT_CONFIG_FILE),
    ):
        self.mod_path = mod_path.expanduser() / "game" / "Mods"
        self.steamcmd = steamcmd.expanduser()
        self.config_path = config_path.expanduser()

    def to_dict(self) -> ConfigPrimitives:
        return {
            "mod_path": str(self.mod_path),
            "config_path": str(self.config_path),
            "steamcmd": str(self.steamcmd),
        }

    def save_config(self):
        if not self.config_path.is_file():
            self.config_path.touch()
        with open(self.config_path, "wb") as file:
            tomli_w.dump(self.to_dict(), file)


def main():
    parser = argparse.ArgumentParser(description="Manage Config using TOML.")
    parser.add_argument(
        "--save", action="store_true", help="Save the config to a TOML file."
    )
    parser.add_argument(
        "--load", action="store_true", help="Load the config from a TOML file."
    )
    parser.add_argument("file_path", type=str, help="Path to the TOML file.")

    args = parser.parse_args()

    if args.save:
        # Example Config object
        config = Config(
            mod_path=Path("/path/to/rimworld/mods"),
            config_path=Path(args.file_path),
        )
        config.save_config()
        print(f"Config saved to {args.file_path}")
    elif args.load:
        config = Config.load_config(args.file_path)
        print("Config loaded:")
        print(f"Mod Path: {config.mod_path}")
        print(f"Config Path: {config.config_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    import argparse

    main()
