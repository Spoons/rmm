#!/usr/bin/env python3

from pathlib import Path
from typing import List, Optional

from . import util


class PathFinder:
    DEFAULT_GAME_PATHS = [
        ("~/GOG Games/RimWorld", "linux"),
        ("~/games/rimworld", "linux"),
        ("~/.local/share/Steam/steamapps/common/RimWorld", "linux"),
        ("/Applications/RimWorld.app/Mods", "darwin"),
        ("~/Library/Application Support/Steam/steamapps/common/RimWorld", "darwin"),
        ("C:/GOG Games/RimWorld/Mods", "win32"),
        ("C:/Program Files (x86)/Steam/steamapps/common/RimWorld", "win32"),
        ("C:/Program Files/Steam/steamapps/common/RimWorld", "win32"),
    ]

    DEFAULT_WORKSHOP_PATHS = [
        ("~/.local/share/Steam/steamapps/workshop/content/294100", "linux"),
        (
            "~/Library/Application Support/Steam/steamapps/workshop/content/294100",
            "darwin",
        ),
        (
            "C:/Program Files (x86)/Steam/steamapps/common/workshop/content/294100",
            "win32",
        ),
        ("C:/Program Files/Steam/steamapps/common/workshop/content/294100", "win32"),
    ]

    DEFAULT_CONFIG_PATHS = [
        ("~/Library/Application Support/RimWorld/", "darwin"),
        ("~/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios", "linux"),
        ("~/AppData/LocalLow/Ludeon Studios/RimWorld by Ludeon Studios", "win32"),
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
        files_to_find = ["Config", "Saves"]
        child_names = [f.name for f in p.iterdir()]
        for target_name in files_to_find:
            if not target_name in child_names:
                return False
        return True

    @staticmethod
    def _search_root(p: Path, f) -> Optional[Path]:
        try:
            p = util.sanitize_path(p)
            for n in p.glob("**/"):
                if f(n):
                    return n
            return None
        except FileNotFoundError:
            return None

    @staticmethod
    def get_workshop_from_game_path(p: Path):
        p = util.sanitize_path(p)
        for index, dirname in enumerate(p.parts):
            if dirname == "steamapps":
                return Path(*list(p.parts[0:index])) / Path(
                    "steamapps/workshop/content/294100"
                )

    @staticmethod
    def _search_defaults(defaults: List[str], f) -> Optional[Path]:
        platform = util.platform()
        for path in [n[0] for n in defaults if n[1] == platform]:
            path = util.sanitize_path(path)
            if path := f(Path(path)):
                return path
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
