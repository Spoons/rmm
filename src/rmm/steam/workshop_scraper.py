import re
from typing import List
import requests
from bs4 import BeautifulSoup
from rmm.steam import WorkshopResult
from rmm.steam.workshop_result import WorkshopDetail


class Scraper:
    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        }
        self.index_query = (
            "https://steamcommunity.com/workshop/browse/?appid=294100&searchtext={}"
        )
        self.detail_query = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"

    def _request(self, url: str, term: str) -> str:
        max_retries = 5
        for _ in range(max_retries):
            try:
                response = requests.get(
                    url.format(term.replace(" ", "+")), headers=self.headers
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException:
                continue
        raise Exception("Failed to retrieve data after multiple retries.")

    def detail(self, steamid: int) -> WorkshopResult:
        html_content = self._request(self.detail_query, str(steamid))
        results = BeautifulSoup(html_content, "html.parser")
        details = results.find_all("div", class_="detailsStatRight")

        size = details[0].get_text() if len(details) > 0 else "Unknown"
        created = details[1].get_text() if len(details) > 1 else "Unknown"
        updated = details[2].get_text() if len(details) > 2 else "Unknown"

        description_div = results.find("div", class_="workshopItemDescription")
        description = (
            description_div.get_text()
            if description_div
            else "No description available"
        )

        return WorkshopDetail(
            steamid=steamid,
            name="Mod Name",  # Placeholder, replace with actual extraction logic if available
            author="Mod Author",  # Placeholder, replace with actual extraction logic if available
            description=description,
            updated=updated,
            size=size,
            created=created,
        )

    def search(self, term: str) -> List[WorkshopResult]:
        html_content = self._request(self.index_query, term)
        page_result = BeautifulSoup(html_content, "html.parser").find_all(
            "div",
        )
        results = []

        for item in page_result:
            try:
                item_title = item.findChild(
                    "div", class_="workshopItemTitle"
                ).get_text()  # type: ignore
                author_name = item.find(
                    "div", class_="workshopItemAuthorName"
                ).get_text()[3:]  # type: ignore
                steamid_match = re.search(r"\d+", item.find("a", class_="ugc")["href"])  # type: ignore
                steamid = int(steamid_match.group()) if steamid_match else 0

                results.append(
                    WorkshopResult(
                        steamid=steamid,
                        name=item_title,
                        author=author_name,
                        description="",  # Placeholder, replace with actual extraction logic if available
                    )
                )
            except (AttributeError, ValueError):
                continue

        return results


def main():
    # Initialize the Scraper
    scraper = Scraper()

    # Example usage of the detail method
    # try:
    #     steam_id = 123456789  # Example Steam ID
    #     workshop_result = scraper.detail(steam_id)
    #     print("Detail Result:")
    #     print(workshop_result)
    # except Exception as e:
    #     print(f"An error occurred while fetching details: {e}")

    # Example usage of the search method
    try:
        search_term = "vanilla expanded"  # Example search term
        search_results = scraper.search(search_term)
        print("\nSearch Results:")
        for result in search_results:
            print(result)
    except Exception as e:
        print(f"An error occurred during search: {e}")


if __name__ == "__main__":
    main()
