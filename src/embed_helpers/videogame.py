from dataclasses import dataclass

from disnake import Embed, Color

from src.embed_helpers.common import Difficulty, Platform, safeGet


@dataclass
class VideoGameObj:
    id: int
    title: str
    minPlayers: int
    maxPlayers: int
    playingTime: int
    copies: int = -1
    copies_available: int = -1
    difficulty: Difficulty = Difficulty.UNDEFINED
    platform: Platform = Platform.UNDEFINED
    thumbnail: str = "https://i.imgur.com/OJhoTqu.png"
    description: str = "No description available"
    categories: list[str] = ()
    length: int = 0

    @staticmethod
    def createFromDB(boardGameDict: dict):
        if "difficulty" in boardGameDict and isinstance(boardGameDict["difficulty"], str):
            boardGameDict["difficulty"] = Difficulty(int(boardGameDict["difficulty"]))
        if "platform" in boardGameDict and isinstance(boardGameDict["platform"], str):
            boardGameDict["platform"] = Platform(int(boardGameDict["platform"]))
        return VideoGameObj(
            id=safeGet(boardGameDict, "id", -1),
            title=safeGet(boardGameDict, "name", "<NO TITLE>"),
            minPlayers=safeGet(boardGameDict, "min_players", -1),
            maxPlayers=safeGet(boardGameDict, "max_players", -1),
            playingTime=safeGet(boardGameDict, "length", -1),
            copies=safeGet(boardGameDict, "copies", 0),
            copies_available=safeGet(boardGameDict, "available_copies", -1),
            difficulty=safeGet(boardGameDict, "difficulty", Difficulty.UNDEFINED),
            platform=safeGet(boardGameDict, "platform", Platform.UNDEFINED),
            thumbnail=safeGet(boardGameDict, "thumbnail", "https://i.imgur.com/OJhoTqu.png"),
            description=safeGet(boardGameDict, "description", "No description available"),
            categories=safeGet(boardGameDict, "categories", []),
            length=safeGet(boardGameDict, "length", 0)
        )

    def getEmbed(self, flags: [str]) -> Embed:
        color = Color.dark_green()
        if self.copies_available >= 0:
            if self.copies_available == 0:
                color = Color.red()
            else:
                color = Color.green()
        embed = Embed(title=self.title, color=color)
        embed.set_thumbnail(url=self.thumbnail)

        if "compact" not in flags:
            embed.add_field(name="Description", value=f"{self.description}", inline=False)

            categoriesStr = "\n".join(self.categories)
            if "allCats" not in flags and len(self.categories) > 3:
                categoriesStr = "\n".join(self.categories[:3]) + "..."
            if len(self.categories) > 0:
                embed.add_field(name="Categories", value=f"{categoriesStr}", inline=True)
            else:
                embed.add_field(name="Categories", value=f"None", inline=True)

        if self.minPlayers == self.maxPlayers:
            embed.add_field(name="Players", value=f"{self.minPlayers}", inline=True)
        else:
            embed.add_field(name="Players", value=f"{self.minPlayers} - {self.maxPlayers}", inline=True)

        embed.add_field(name="Playing Time", value=f"{self.playingTime} minutes", inline=True)

        if "compact" not in flags and self.difficulty != Difficulty.UNDEFINED:
            embed.add_field(name="Difficulty", value=f"{self.difficulty.name.lower()}", inline=True)

        embed.add_field(name="Platform", value=f"{self.platform.name.lower()}", inline=True)
        if self.copies != -1:
            embed.add_field(name="Copies", value=f"{self.copies}", inline=True)
        if self.copies_available != -1:
            embed.add_field(name="Available Copies", value=f"{self.copies_available}", inline=True)
        return embed

    def getInsertQueries(self, nextID: int) -> [(str, list)]:
        queries = []
        self.id = nextID
        insertVideoGameQuery = "INSERT INTO videogames (id, min_players, max_players, playing_time, difficulty, platform) VALUES (?, ?, ?, ?, ?, ?);"
        insertVideoGameValues = [self.id, self.minPlayers, self.maxPlayers, self.playingTime, self.difficulty.value, self.platform.value]
        queries.append((insertVideoGameQuery, insertVideoGameValues))
        insertItemQuery = "INSERT INTO items (id, name, length, description, thumbnail, type, copies) VALUES (?, ?, ?, ?, ?, ?, ?);"
        insertItemValues = [self.id, self.title, self.length, self.description, self.thumbnail, "videogame", self.copies]
        queries.append((insertItemQuery, insertItemValues))
        for category in self.categories:
            insertCategoryQuery = "INSERT INTO categories (id, category) VALUES (?, ?);"
            insertCategoryValues = [self.id, category]
            queries.append((insertCategoryQuery, insertCategoryValues))
        return queries

    def getDict(self):
        return {
            "id": self.id,
            "name": self.title,
            "min_players": self.minPlayers,
            "max_players": self.maxPlayers,
            "playing_time": self.playingTime,
            "difficulty": self.difficulty.value,
            "platform": self.platform.value,
            "thumbnail": self.thumbnail,
            "description": self.description,
            "categories": self.categories,
            "length": self.length
        }