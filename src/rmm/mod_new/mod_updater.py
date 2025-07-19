from pathlib import Path
from typing import List
from rmm import Mod
from rmm import setup_logging
from rmm.steam import SteamDownloader
import shutil

logger = setup_logging(__name__)


class NoSteamId(Exception):
    pass


class ModUpdater:
    def __init__(self, mod_install_path: Path, downloader: SteamDownloader):
        """
        Initialize the ModUpdater with the path to the mod installation directory.

        :param mod_install_path: Path to the directory where mods are installed.
        """
        self.mod_install_path = mod_install_path
        self.steam_downloader = downloader

    def update_mod(self, mod: Mod) -> None:
        """
        Update a single mod using SteamDownloader.

        :param mod: The Mod object representing the mod to update.
        :return: True if the update was successful, False otherwise.
        """
        logger.debug(f"updating mod {mod.name} by {mod.author}")
        try:
            if not mod.steam_id:
                raise NoSteamId()
            # Use SteamDownloader to download the mod
            downloaded_mods, download_path = self.steam_downloader.download(
                mod.steam_id
            )

            # Assuming the downloaded mod is the first one in the list
            if not downloaded_mods:
                print(f"No mods downloaded for ID: {mod.steam_id}")

            downloaded_mod = downloaded_mods[0]

            # Move the downloaded mod to the mod installation directory
            destination_path = self.mod_install_path / str(downloaded_mod.id)
            mod_path = download_path / str(mod.steam_id)
            if download_path.exists():
                shutil.rmtree(destination_path)
                # Move the directory
                shutil.copytree(mod_path, destination_path)
                print(f"Mod {mod.name} updated successfully.")
            else:
                print(f"Mod {mod.name} not found in the download directory.")
        except Exception as e:
            print(f"An error occurred while updating mod {mod.name}: {e}")

    def update_all_mods(self, mods: List[Mod]) -> None:
        """
        Update all mods in the provided list.
        :param mods: A list of Mod objects to update.
        """
        valid_mod_ids = [m.steam_id for m in mods if m.steam_id]
        logger.debug(f"valid mod ids: {valid_mod_ids}")
        dw_mods, dw_path = self.steam_downloader.download(*valid_mod_ids)

        if not dw_path.exists():
            raise Exception("Download path not found")

        for mod in dw_mods:
            destination_path = self.mod_install_path / str(mod.id)
            mod_path = dw_path / str(mod.steam_id)
            shutil.rmtree(destination_path)
            # Move the directory
            shutil.copytree(mod_path, destination_path)
            print(f"Mod {mod.name} updated successfully.")
