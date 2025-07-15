import re
import urllib.error
import urllib.request
from typing import List

from bs4 import BeautifulSoup


STEAMCMD_WINDOWS_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"


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
