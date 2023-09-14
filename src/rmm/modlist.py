#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
from pathlib import Path
from typing import Any, Generator, Iterator, cast

from .mod import Mod


class ModListSerializer(ABC):
    @classmethod
    @abstractmethod
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        pass

    @classmethod
    @abstractmethod
    def serialize(cls, mods: MutableSequence) -> Generator[str, None, None]:
        pass


class CsvStringBuilder:
    def __init__(self):
        self.value = []

    def write(self, row: str) -> None:
        self.value.append(row)

    def pop(self) -> None:
        return self.value.pop()

    def __iter__(self) -> Iterator[str]:
        return iter(self.value)


class ModListV2Format(ModListSerializer):
    HEADER = {"PACKAGE_ID": 0, "STEAM_ID": 1, "REPO_URL": 2}
    MAGIC_FLAG = "RMM_V2_MODLIST"

    @classmethod
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        reader = csv.reader(text.split("\n"))
        for parsed in reader:
            try:
                yield Mod(
                    packageid=parsed[cls.HEADER["PACKAGE_ID"]],
                    steamid=int(parsed[cls.HEADER["STEAM_ID"]]),
                    repo_url=parsed[cls.HEADER["REPO_URL"]] if not "" else None,
                )
            except IndexError:
                if parsed:
                    print("Unable to import: ", parsed)
                continue
            except ValueError:
                yield Mod(
                    packageid=parsed[cls.HEADER["PACKAGE_ID"]],
                    repo_url=parsed[cls.HEADER["REPO_URL"]] if not "" else None,
                )
                continue

    @classmethod
    def serialize(cls, mods: MutableSequence) -> Generator[str, None, None]:
        buffer = CsvStringBuilder()
        writer = csv.writer(cast(Any, buffer))
        for m in mods:
            writer.writerow(cls.format(m))
            yield buffer.pop().strip()

    @classmethod
    def format(cls, mod: Mod) -> list[str]:
        return cast(
            list[str],
            [
                mod.packageid,
                str(mod.steamid) if not None else "",
                mod.repo_url if not None else "",
            ],
        )


class ModListV1Format(ModListSerializer):
    STEAM_ID = 0

    @classmethod
    def parse(cls, text: str) -> Generator[Mod, None, None]:
        name_exp = re.compile("(.*) by (.*)")
        for line in text.split("\n"):
            parsed = line.split("#", 1)
            name = None
            author = None
            if len(parsed) == 2:
                matches = re.findall(name_exp, parsed[1])
                if matches and len(matches[0]) == 2:
                    name = matches[0][0]
                    author = matches[0][1]
            try:
                yield Mod(
                    steamid=int(
                        parsed[cls.STEAM_ID]
                        .strip()
                        .encode("ascii", errors="ignore")
                        .decode()
                    ),
                    name=name,
                    author=author,
                )
            except ValueError:
                if line:
                    print("Unable to import: ", line)
                continue

    @classmethod
    def serialize(cls, mods: MutableSequence) -> Generator[str, None, None]:
        for m in mods:
            yield cls.format(m)

    @classmethod
    def format(cls, mod: Mod) -> str:
        return "{}# {} by {} ".format(str(mod.steamid), mod.name, mod.author)


class ModListFile:
    @staticmethod
    def read(path: Path) -> list[Mod]:
        try:
            with path.open("r") as f:
                text = f.read()
        except OSError as e:
            print(e)
            return None

        if re.search(r"^\s?[0-9]+\s?#.*$", text, re.MULTILINE):
            return [m for m in ModListV1Format.parse(text)]

        return [m for m in ModListV2Format.parse(text)]

    @staticmethod
    def write(path: Path, mods: MutableSequence, serializer: ModListSerializer) -> bool:
        try:
            with path.open("w+") as f:
                [f.write(line + "\n") for line in serializer.serialize(mods)]
        except OSError as e:
            print(e)
            return False
        return True
