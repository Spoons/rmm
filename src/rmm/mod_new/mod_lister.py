from rmm import Mod
from rmm.manager import Manager


class ModLister:
    def __init__(self, manager: Manager):
        self.manager = manager

    def list_mods(self) -> list[Mod]:
        """List all installed mods."""
        return self.manager.installed_mods()

    def display_mods(self):
        """Display the list of installed mods."""
        mods = self.list_mods()
        for mod in mods:
            print(mod)
