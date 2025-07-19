from rmm import Mod
from rmm.config import Config  # Assuming you have a Mod class defined elsewhere


class Manager:
    """
    A class to manage RimWorld mods.
    This class will handle operations such as installing, removing, enabling, disabling, and listing mods.
    """

    def __init__(self, config: Config):
        """
        Initialize the Manager with a configuration.

        :param config: Configuration object containing paths and settings.
        """
        self.config = config

    def installed_mods(self) -> list[Mod]:
        """
        List all installed mods.

        :return: A list of Mod objects representing the installed mods.
        """
        mod_path = self.config.mod_path

        # Assuming each mod is in its own directory within the mod_path
        mods: list[Mod] = [
            Mod.create_from_path(mod_dir)
            for mod_dir in mod_path.iterdir()
            if mod_dir.is_dir()
        ]
        return mods

    def find_one_mod(self, id: int) -> Mod:
        mods = self.installed_mods()

        mod_set = set(filter(lambda m: m.steam_id == id, mods))
        if len(mod_set) == 0:
            raise NoModsFound()
        if len(mod_set) > 1:
            raise TooManyMatchingMods()
        return mod_set.pop()


class NoModsFound(Exception):
    pass


class TooManyMatchingMods(Exception):
    pass
