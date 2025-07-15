import tempfile
from pathlib import Path
from rmm import util
from rmm import Mod, ModFolder


class SteamDownloader:
    """Interacts and manages the `steamcmd` client"""

    def find_path(self) -> tuple[Path, Path]:
        home_path = None
        mod_path = None

        try:
            for d in Path(tempfile.gettempdir()).iterdir():
                if d.name.startswith("rmm-") and d.is_dir() and (d / ".rmm").is_file():
                    home_path = d
                    break
        except FileNotFoundError:
            pass

        if not home_path:
            home_path = Path(tempfile.mkdtemp(prefix="rmm-"))
            with open(home_path / ".rmm", "w"):
                pass

        try:
            mod_path = home_path / util.extract_download_path()
        except Exception as e:
            print(f"could not find download path...: {e}")
            raise e

        return home_path, mod_path

    def download(self, mods: list[int]) -> tuple[list[Mod], Path]:
        home_path, mod_path = self.find_path()

        if not home_path:
            raise Exception("Error: Could not get temporary directory")

        workshop_item_arg = " +workshop_download_item 294100 "

        query = 'env HOME="{}" steamcmd +login anonymous {} +quit >&2'.format(
            str(home_path),
            workshop_item_arg + workshop_item_arg.join(str(m) for m in mods),
        )
        util.run_sh(query)

        return ModFolder().read(mod_path), mod_path
