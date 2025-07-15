import subprocess
import shutil
from pathlib import Path


class ModInstaller:
    def __init__(self, steamcmd_path: Path, mod_install_path: Path):
        self.steamcmd_path = steamcmd_path
        self.mod_install_path = mod_install_path

    def download_mod(self, mod_id: str) -> bool:
        """
        Download a mod from the Steam Workshop using SteamCMD.

        :param mod_id: The ID of the mod to download.
        :return: True if the download was successful, False otherwise.
        """
        try:
            # Command to download the mod using SteamCMD
            command = [
                str(self.steamcmd_path),
                "+login",
                "anonymous",
                "+workshop_download_item",
                "294100",
                mod_id,
                "+quit",
            ]

            # Execute the command
            result = subprocess.run(command, check=True, capture_output=True, text=True)

            # Check if the command was successful
            if result.returncode == 0:
                print(f"Mod {mod_id} downloaded successfully.")
                return True
            else:
                print(f"Failed to download mod {mod_id}.")
                return False
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while downloading mod {mod_id}: {e}")
            return False

    def install_mod(self, mod_id: str) -> bool:
        """
        Install a mod by downloading it and moving it to the mod directory.

        :param mod_id: The ID of the mod to install.
        :return: True if the installation was successful, False otherwise.
        """
        # Download the mod
        if not self.download_mod(mod_id):
            return False

        # Define paths
        download_path = (
            self.steamcmd_path.parent
            / "steamapps"
            / "workshop"
            / "content"
            / "294100"
            / mod_id
        )
        install_path = self.mod_install_path / mod_id

        try:
            # Move the downloaded mod to the mod directory
            if download_path.exists():
                shutil.move(str(download_path), str(install_path))
                print(f"Mod {mod_id} installed successfully.")
                return True
            else:
                print(f"Mod {mod_id} not found in the download directory.")
                return False
        except Exception as e:
            print(f"An error occurred while installing mod {mod_id}: {e}")
            return False


if __name__ == "__main__":
    steamcmd_path = Path("/path/to/steamcmd")  # Path to the SteamCMD executable
    mod_install_path = Path("/path/to/mods")  # Path to the mod installation directory

    mod_installer = ModInstaller(steamcmd_path, mod_install_path)
    mod_installer.install_mod("123456789")  # Example mod ID
