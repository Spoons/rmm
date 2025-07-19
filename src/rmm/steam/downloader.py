import subprocess
import tempfile
from pathlib import Path
from rmm import Mod, ModFolder
from rmm.logger import setup_logging


logger = setup_logging(__name__)


class SteamCMDNotFound(Exception):
    pass


class SteamDownloader:
    """Interacts and manages the `steamcmd` client"""

    MOD_PATH = Path("Steam/steamapps/workshop/content/294100")

    def __init__(self, steamcmd_path: Path) -> None:
        if not steamcmd_path.is_file():
            raise SteamCMDNotFound(steamcmd_path)
        self.steamcmd_path = steamcmd_path

    def get_temp_path(self) -> Path:
        home_path = Path(tempfile.mkdtemp(prefix="rmm-"))
        (home_path / ".rmm").touch(exist_ok=True)

        return home_path

    def download(self, *mod_ids: int) -> tuple[list[Mod], Path]:
        home_path = self.get_temp_path()

        if not home_path:
            raise Exception("Could not get temporary directory")

        command = [
            self.steamcmd_path,
            "+login",
            "anonymous",
            *list(map(lambda id: f"+workshop_download_item 294100 {id}", mod_ids)),
            "+quit",
        ]

        logger.debug(command)

        result = subprocess.run(
            command, check=True, capture_output=True, text=True, env={"HOME": home_path}
        )

        if result.returncode == 0:
            print(f"Downloaded {len(mod_ids)} mods successfully.")
        else:
            raise ModDownloadError()

        return ModFolder().read(home_path / self.MOD_PATH), home_path / self.MOD_PATH


class ModDownloadError(Exception):
    pass
