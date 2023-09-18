from dataclasses import dataclass
from .about import ModAboutXML


@dataclass
class Mod(ModAboutXML):
    steam_id: int

    def __init__(self, steam_id: int, about: ModAboutXML):
        super().__init__(
            about.package_id,
            about.before,
            about.after,
            about.incompatible,
            about.author,
            about.name,
            about.supported_versions,
            about.dependencies,
        )
        self.steam_id = steam_id
