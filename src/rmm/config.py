#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    def __init__(
        self,
        path: Path = None,
        workshop_path: Optional[Path] = None,
        config_path: Path = None,
    ):
        self.mod_path = path
        self.workshop_path = workshop_path
        self.config_path = config_path
        self.modsconfig_path = None
        self.USE_HUMAN_NAMES = True
