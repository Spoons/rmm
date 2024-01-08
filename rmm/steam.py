#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Tuple

from bs4 import BeautifulSoup

from . import util
from .mod import Mod, ModFolder

STEAMCMD_WINDOWS_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"


class SteamDownloader:
    @staticmethod
    def download_steamcmd_windows(path):
        download_path = path / "steamcmd.zip"
        max_retries = 10
        print("Installing SteamCMD")
        for count in range(max_retries + 1):
            try:
                urllib.request.urlretrieve(STEAMCMD_WINDOWS_URL, download_path)
            except urllib.error.URLError as e:
                if count < max_retries:
                    continue
                raise e

        print("Extracting steamcmd.zip...")
        with zipfile.ZipFile(download_path, "r") as zr:
            zr.extractall(path)

        os.chdir(path)
        try:
            for n in util.execute("steamcmd +login anonymous +quit"):
                print(n, end="")
        except subprocess.CalledProcessError:
            pass

    @staticmethod
    def find_path():
        home_path = None
        mod_path = None
        try:
            for d in Path(tempfile.gettempdir()).iterdir():
                if d.name[0:4] == "rmm-" and d.is_dir() and (d / ".rmm").is_file():
                    home_path = d
                    break
        except FileNotFoundError:
            pass

        if util.platform() == "win32":
            home_path = Path(tempfile.gettempdir()) / "rmm"
            home_path.mkdir(parents=True, exist_ok=True)

        if not home_path:
            home_path = Path(tempfile.mkdtemp(prefix="rmm-"))
            with open((home_path / ".rmm"), "w"):
                pass

        if not home_path:
            raise Exception("Error could not get temporary directory")

        if util.platform() == "win32":
            mod_path = home_path / "SteamApps/workshop/content/294100/"
        elif util.platform() == "darwin":
            mod_path = (
                home_path
                / "Library/Application Support/Steam/SteamApps/workshop/content/294100/"
            )
        else:
            mod_path = home_path / util.extract_download_path()
        return (home_path, mod_path)

    @staticmethod
    def download(mods: List[int]) -> Tuple[List[Mod], Path]:
        home_path, mod_path = SteamDownloader.find_path()

        if not home_path:
            raise Exception("Error could not get temporary directory")

        workshop_item_arg = " +workshop_download_item 294100 "
        if util.platform() == "win32":
            os.chdir(home_path)
            if not (home_path / "steamcmd.exe").exists():
                SteamDownloader.download_steamcmd_windows(home_path)

            query = "steamcmd +login anonymous {} +quit".format(
                workshop_item_arg + workshop_item_arg.join(str(m) for m in mods),
            )
            print()
            for n in util.execute(query):
                print(n, end="")
        else:
            query = 'env HOME="{}" steamcmd +login anonymous {} +quit >&2'.format(
                str(home_path),
                workshop_item_arg + workshop_item_arg.join(str(m) for m in mods),
            )
            util.run_sh(query)

        # TODO: ugly work around for weird steam problem
        if util.platform() == "linux" and not mod_path.exists():
            mod_path = SteamDownloader.replace_path(mod_path)

        return (ModFolder.read(mod_path), mod_path)

    @staticmethod
    def replace_path(path):
        path_parts = []
        found = False
        for n in reversed(path.parts):
            if n == ".steam" and found == False:
                path_parts.append("Steam")
                found = True
            else:
                path_parts.append(n)

        return Path(*reversed(path_parts))


class WorkshopResult:
    def __init__(
        self,
        steamid,
        name=None,
        author=None,
        description=None,
        update_time=None,
        size=None,
        # num_rating=None,
        rating=None,
        create_time=None,
        num_ratings=None,
    ):
        self.steamid = steamid
        self.name = name
        self.author = author
        self.description = description
        self.update_time = update_time
        self.size = size
        self.create_time = create_time
        self.num_ratings = num_ratings
        self.rating = rating

    def __str__(self):
        return "\n".join(
            [
                prop + ": " + str(getattr(self, prop))
                for prop in self.__dict__
                if not callable(self.__dict__[prop])
            ]
        )

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkshopResult):
            raise NotImplementedError
        return self.steamid == other.steamid


class WorkshopWebScraper:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    }
    index_query = (
        "https://steamcommunity.com/workshop/browse/?appid=294100&searchtext={}"
    )
    detail_query = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"

    @classmethod
    def _request(cls, url: str, term: str):
        max_retries = 5
        for n in range(max_retries + 1):
            try:
                return urllib.request.urlopen(
                    urllib.request.Request(
                        url.format(term.replace(" ", "+")),
                        headers=WorkshopWebScraper.headers,
                    )
                )
            except urllib.error.URLError as e:
                if n < max_retries:
                    continue
                raise e

    @classmethod
    def detail(cls, steamid: int) -> WorkshopResult:
        results = BeautifulSoup(
            cls._request(cls.detail_query, str(steamid)),
            "html.parser",
        )

        details = results.find_all("div", class_="detailsStatRight")
        try:
            size = details[0].get_text()
        except IndexError:
            size = None
        try:
            created = details[1].get_text()
        except IndexError:
            created = None
        try:
            updated = details[2].get_text()
        except IndexError:
            updated = None
        try:
            description = results.find("div", class_="workshopItemDescription")
            if description:
                description = description.get_text()
        except AttributeError:
            description = None
        try:
            num_ratings = results.find("div", class_="numRatings")
            if num_ratings:
                num_ratings = num_ratings.get_text()
        except AttributeError:
            num_ratings = None
        try:
            rating = re.search(
                "([1-5])(?:-star)",
                str(results.find("div", class_="fileRatingDetails").img),
            )
            if rating:
                rating = rating.group(1)
        except AttributeError:
            rating = None

        return WorkshopResult(
            steamid,
            size=size,
            create_time=created,
            update_time=updated,
            description=description,
            # num_rating=num_ratings,
            rating=rating,
        )

    @classmethod
    def search(cls, term: str, reverse: bool = False) -> List[WorkshopResult]:
        page_result = BeautifulSoup(
            cls._request(cls.index_query, term),
            "html.parser",
        ).find_all("div", class_="workshopItem")

        results = []
        for r in page_result:
            try:
                item_title = r.find("div", class_="workshopItemTitle").get_text()
                author_name = r.find("div", class_="workshopItemAuthorName").get_text()[
                    3:
                ]
                steamid = int(
                    re.search(r"\d+", r.find("a", class_="ugc")["href"]).group()
                )
            except (AttributeError, ValueError):
                continue
            results.append(WorkshopResult(steamid, name=item_title, author=author_name))

        if reverse:
            return list(reversed(results))
        return results
