#!/usr/bin/env python3

from pathlib import Path
from typing import Optional


class PathFinder:
    DEFAULT_GAME_PATHS = [
        "~/GOG Games/RimWorld",
        "~/.local/share/Steam/steamapps/common/RimWorld",
        "/Applications/Rimworld.app/Mods",
    ]

    DEFAULT_WORKSHOP_PATHS = ["~/.local/share/Steam/steamapps/workshop/content/294100"]

    DEFAULT_CONFIG_PATHS = [
        "~/Library/Application Support/Rimworld/",
        "~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios",
    ]

    @staticmethod
    def _is_game_dir(p: Path) -> bool:
        if p.name == "Mods":
            for n in p.parent.iterdir():
                if n.name == "Version.txt":
                    return True
        return False

    @staticmethod
    def _is_workshop_dir(p: Path) -> bool:
        return (
            p.name == "294100"
            and p.parts[-2] == "content"
            and p.parts[-3] == "workshop"
        )

    @staticmethod
    def _is_config_dir(p: Path) -> bool:
        files_to_find = ["Config", "prefs", "Saves"]
        child_names = [f.name for f in p.iterdir()]
        for target_name in files_to_find:
            if not target_name in child_names:
                return False
        return True

    @staticmethod
    def _search_root(p: Path, f) -> Optional[Path]:
        p = p.expanduser()
        for n in p.glob("**/"):
            if f(n):
                return n
        return None

    @staticmethod
    def get_workshop_from_game_path(p: Path):
        p = p.expanduser()
        for index, dirname in enumerate(p.parts):
            if dirname == "steamapps":
                return Path(*list(p.parts[0:index])) / Path(
                    "steamapps/workshop/content/294100"
                )

    @staticmethod
    def _search_defaults(defaults: list[str], f) -> Optional[Path]:
        for p in defaults:
            if p := f(Path(p)):
                return p
        return None

    @classmethod
    def find_game(cls, p: Path) -> Optional[Path]:
        return cls._search_root(p, cls._is_game_dir)

    @classmethod
    def find_workshop(cls, p: Path) -> Optional[Path]:
        return cls._search_root(p, cls._is_workshop_dir)

    @classmethod
    def find_config(cls, p: Path) -> Optional[Path]:
        return cls._search_root(p, cls._is_config_dir)

    @classmethod
    def find_game_defaults(cls) -> Optional[Path]:
        return cls._search_defaults(cls.DEFAULT_GAME_PATHS, cls.find_game)

    @classmethod
    def find_workshop_defaults(cls) -> Optional[Path]:
        return cls._search_defaults(cls.DEFAULT_WORKSHOP_PATHS, cls.find_workshop)

    @classmethod
    def find_config_defaults(cls) -> Optional[Path]:
        return cls._search_defaults(cls.DEFAULT_CONFIG_PATHS, cls.find_config)
