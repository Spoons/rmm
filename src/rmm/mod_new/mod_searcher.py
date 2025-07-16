from rmm.steam.workshop_scraper import Scraper


class ModSearcher:
    def __init__(self):
        self.scraper = Scraper()

    def search(self, term: str):
        results = self.scraper.search(term)
        return results

    def display_search(self, term: str):
        results = self.search(term)
        for result in reversed(results):
            print(result)
