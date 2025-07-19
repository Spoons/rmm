import shutil
from pathlib import Path

from rmm.logger import setup_logging
from rmm.steam.downloader import SteamDownloader


logger = setup_logging(__name__)


class ModInstaller:
    def __init__(self, mod_install_path: Path, downloader: SteamDownloader):
        self.mod_install_path = mod_install_path
        self.downloader = downloader

    def install_mod(self, mod_id: int):
        """
        Download a mod from the Steam Workshop using SteamCMD.

        :param mod_id: The ID of the mod to download.
        :return: True if the download was successful, False otherwise.
        """
        dw_mods, dw_path = self.downloader.download(mod_id)

        if not dw_path.exists():
            raise Exception("Download path not found")

        for mod in dw_mods:
            destination_path = self.mod_install_path / str(mod.id)
            mod_path = dw_path / str(mod.steam_id)
            shutil.copytree(mod_path, destination_path)
            logger.info(f"Mod {mod.name} installed successfully.")
