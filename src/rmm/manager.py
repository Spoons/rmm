#!/usr/bin/env python3

from pathlib import Path

from typing import cast
import rmm.util as util
from rmm.config import Config
from rmm.mod import Mod, ModFolder, EXPANSION_PACKAGES
from rmm.modsconfig import ModsConfig
from rmm.steam import SteamDownloader, WorkshopResult


class Manager:
    def __init__(self, config: Config):
        if not isinstance(config, Config):
            raise Exception("Must pass Config object to Manager")
        self.config = config
        if self.config.modsconfig_path:
            self.modsconfig = ModsConfig(self.config.modsconfig_path)

    def install_mod(self, steam_cache: Path, steamid: int):
        if not steamid:
            raise Exception("Missing SteamID")
        mod = Mod.create_from_path(steam_cache / str(steamid))

        dest_path = None
        if self.config.USE_HUMAN_NAMES and mod and mod.packageid:
            dest_path = self.config.mod_path / mod.packageid
        else:
            dest_path = self.config.mod_path / str(steamid)

        if dest_path:
            util.copy(
                steam_cache / str(steamid),
                dest_path,
                recursive=True,
            )
        else:
            print(f"Unable to install mod: {steamid}")
            return False
        return True

    def remove_mod(self, mod: Mod):
        if not self.config.mod_path:
            raise Exception("Game path not defined")

        installed_mods = ModFolder.read(self.config.mod_path)
        removal_queue = [n for n in installed_mods if n == mod]

        for m in removal_queue:
            print(f"Uninstalling {mod.title()}")
            mod_absolute_path = self.config.mod_path / m.dirname
            if mod_absolute_path:
                util.remove(mod_absolute_path)

            steamid_path = self.config.mod_path / str(m.steamid)
            if m.steamid and steamid_path.exists():
                util.remove(self.config.mod_path / str(m.steamid))

            pid_path = self.config.mod_path / m.packageid
            if self.config.USE_HUMAN_NAMES and m.packageid and pid_path.exists():
                util.remove(pid_path)

    def remove_mods(self, queue: list[Mod]):
        for mod in queue:
            if isinstance(mod, WorkshopResult):
                mod = Mod.create_from_workshorp_result(mod)
            self.remove_mod(mod)

    def sync_mods(self, queue: list[Mod] | list[WorkshopResult]):
        (_, steam_cache_path) = SteamDownloader.download(
            [mod.steamid for mod in queue if mod.steamid]
        )
        # game_dir_mods = ModFolder.read(config.game_path)

        for mod in queue:
            if isinstance(mod, WorkshopResult):
                mod = Mod.create_from_workshorp_result(mod)
            if not isinstance(mod.steamid, int):
                continue
            success = False
            try_install = False
            try:
                self.remove_mod(mod)
                success = self.install_mod(steam_cache_path, mod.steamid)
            except FileNotFoundError:
                print(
                    f"Unable to download and install {mod.title()}\n\tDoes this mod still exist?"
                )
            if success:
                print(f"Installed {mod.title()}")

    def _mod_config_state(self, mods):
        if self.modsconfig:
            enabled_mods = self.enabled_mods()
            for n in mods:
                if n in enabled_mods:
                    n.enabled = True
                else:
                    n.enabled = False
        return mods
    def installed_mods(self):
        mods = ModFolder.read(self.config.mod_path)
        return self._mod_config_state(mods)

    def search_installed(self, term):
        mods = ModFolder.search(self.config.mod_path, term)
        return self._mod_config_state(mods)

    def enabled_mods(self):
        return self.modsconfig.mods

    def disabled_mods(self):
        enabled_mods = self.enabled_mods()
        installed_mods = self.installed_mods()
        return util.list_loop_exclusion(installed_mods, enabled_mods)

    def _enable_mod(self, mod: str|Mod):
        if isinstance(mod, str):
            mod = Mod(packageid=mod)
        if not mod.packageid:
            raise Exception("No package id for specifed mod")
        self.modsconfig.enable_mod(mod)

    def enable_mods(self, mods):
        for n in mods:
            print("Enabling " + n.title())
            self._enable_mod(n)
        print("Updating ModsConfig.xml")
        self.modsconfig.write()


    def _disable_mod(self, mod: str|Mod):
        if isinstance(mod, str):
            mod = Mod(packageid=mod)
        if not mod.packageid:
            raise Exception("No package id for specifed mod")
        self.modsconfig.disable_mod(mod)

    def disable_mods(self, mods):
        for n in mods:
            print("Disabling " + n.title())
            self._disable_mod(n)
        print("Updating ModsConfig.xml")
        self.modsconfig.write()

    def verify_mods(self):
        return self.modsconfig.verify_state(self.installed_mods())

    def sort_mods(self):
        self.modsconfig.autosort(self.installed_mods(), self.config)

    def order_mods(self):
        enabled_mods = self.enabled_mods()
        installed_mods = self.installed_mods()

        sorted_mods = []
        for m in enabled_mods:
            for j,im in enumerate(installed_mods + EXPANSION_PACKAGES):
                if m == im:
                    sorted_mods.append(im)
                    break

        return sorted_mods
