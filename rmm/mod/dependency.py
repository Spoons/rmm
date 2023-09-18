from dataclasses import dataclass


@dataclass
class ModDep:
    package_id: str
    name: str
    workshop_url: str
    download_url: str
