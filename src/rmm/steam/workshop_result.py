class WorkshopResult:
    def __init__(
        self,
        steamid: int,
        name: str,
        author: str,
        description: str,
    ):
        self.steamid = steamid
        self.name = name
        self.author = author
        self.description = description

    def __str__(self) -> str:
        return f"[{self.author}] {self.name}: {self.description}"[:75]

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkshopResult):
            return NotImplemented
        return self.steamid == other.steamid


class WorkshopDetail(WorkshopResult):
    def __init__(
        self,
        steamid: int,
        name: str,
        author: str,
        description: str,
        updated: str,
        size: str,
        created: str,
    ):
        super().__init__(steamid, name, author, description)
        self.update_time = (updated,)
        self.size = (size,)
        self.create_time = (created,)
