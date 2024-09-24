from dataclasses import dataclass

from disnake import Embed, Color

from src.embed_helpers.common import Difficulty, Platform


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
            id=boardGameDict["id"] if "id" in boardGameDict else -1,
            title=boardGameDict["name"],
            minPlayers=boardGameDict["min_players"],
            maxPlayers=boardGameDict["max_players"],
            playingTime=boardGameDict["length"],
            copies=boardGameDict["copies"] if "copies" in boardGameDict else 0,
            copies_available=boardGameDict["available_copies"] if "available_copies" in boardGameDict else -1,
            difficulty=boardGameDict["difficulty"] if "difficulty" in boardGameDict else Difficulty.UNDEFINED,
            platform=boardGameDict["platform"] if "platform" in boardGameDict else Platform.UNDEFINED,
            thumbnail=boardGameDict["thumbnail"] if "thumbnail" in boardGameDict else "https://i.imgur.com/OJhoTqu.png",
            description=boardGameDict["description"] if "description" in boardGameDict else "No description available",
            categories=boardGameDict["categories"] if "categories" in boardGameDict else [],
            length=boardGameDict["length"] if "length" in boardGameDict else 0
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

        if "compact" not in flags:
            embed.add_field(name="Difficulty", value=f"{self.difficulty.name.lower()}", inline=True)

        embed.add_field(name="Platform", value=f"{self.platform.name.lower()}", inline=True)
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