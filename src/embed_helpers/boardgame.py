from dataclasses import dataclass
from html import unescape
from disnake import Embed, Color

from src.embed_helpers.common import Difficulty, safeGet

BASE_URL: str = f'https://boardgamegeek.com/boardgame/'


@dataclass
class BoardGameObj:
    id: int
    title: str
    minPlayers: int
    maxPlayers: int
    playingTime: int
    copies: int
    copies_available: int
    bggId: int = -1
    description: str = "No description available"
    learn_difficulty: Difficulty = Difficulty.UNDEFINED
    play_difficulty: Difficulty = Difficulty.UNDEFINED
    categories: list[str] = ()
    rank: int = -1
    averageRating: float = -1.0
    bggRating: float = -1.0
    thumbnail: str = "https://i.imgur.com/OJhoTqu.png"

    @staticmethod
    def createFromDB(boardGameDict: dict):
        if "play_difficulty" in boardGameDict and isinstance(boardGameDict["play_difficulty"], str):
            boardGameDict["play_difficulty"] = Difficulty(int(boardGameDict["play_difficulty"]))
        if "learn_difficulty" in boardGameDict and isinstance(boardGameDict["learn_difficulty"], str):
            boardGameDict["learn_difficulty"] = Difficulty(int(boardGameDict["learn_difficulty"]))
        return BoardGameObj(
            id=safeGet(boardGameDict, "id", -1),
            title=safeGet(boardGameDict, "name", "<NO NAME ERROR>"),
            minPlayers=safeGet(boardGameDict, "min_players", 0),
            maxPlayers=safeGet(boardGameDict, "max_players", 0),
            playingTime=safeGet(boardGameDict, "length", 0),
            copies=safeGet(boardGameDict, "copies", 0),
            copies_available=safeGet(boardGameDict, "available_copies", 0),
            bggId=safeGet(boardGameDict, "bgg_id", -1),
            description=safeGet(boardGameDict, "description", "No description available"),
            learn_difficulty=safeGet(boardGameDict, "learn_difficulty", Difficulty.UNDEFINED),
            play_difficulty=safeGet(boardGameDict, "play_difficulty", Difficulty.UNDEFINED),
            categories=safeGet(boardGameDict, "categories", []),
            rank=safeGet(boardGameDict, "bgg_rank", -1),
            averageRating=safeGet(boardGameDict, "bgg_average_rating", -1.0),
            bggRating=safeGet(boardGameDict, "bgg_rating", -1.0),
            thumbnail=safeGet(boardGameDict, "thumbnail", "https://i.imgur.com/OJhoTqu.png")
        )

    @staticmethod
    def createFromBGG(bggDict: dict, extraData: dict = None):
        if isinstance(bggDict["@id"], str):
            bggDict["@id"] = int(bggDict["@id"])
        if extraData is None:
            extraData = {}

        if "play_difficulty" in extraData and isinstance(extraData["play_difficulty"], str):
            extraData["play_difficulty"] = Difficulty(int(extraData["play_difficulty"]))
        if "learn_difficulty" in extraData and isinstance(extraData["learn_difficulty"], str):
            extraData["learn_difficulty"] = Difficulty(int(extraData["learn_difficulty"]))
        description = safeGet(bggDict, "description", "<NO DESCRIPTION>")
        return BoardGameObj(
            id=safeGet(extraData, "id", -1),
            title=safeGet(bggDict, ["name/@value", "name/0/@value"], "<NO NAME ERROR>"),
            minPlayers=int(safeGet(bggDict, "minplayers/@value", -1)),
            maxPlayers=int(safeGet(bggDict, "maxplayers/@value", -1)),
            playingTime=int(safeGet(bggDict, "playingtime/@value", -1)),
            copies=safeGet(extraData, "copies", -1),
            copies_available=safeGet(extraData, "available_copies", -1),
            bggId=int(safeGet(bggDict, "@id", "-1")),
            description=description if len(description) < 1024 else description[:1020] + "...",
            learn_difficulty=safeGet(extraData, "learn_difficulty", Difficulty.UNDEFINED),
            play_difficulty=safeGet(extraData, "play_difficulty", Difficulty.UNDEFINED),
            categories=[safeGet(category, "@value", "Unknown") for category in safeGet(bggDict, "link", []) if safeGet(category, "@type", "") == "boardgamecategory"],
            rank=safeGet(bggDict, ["statistics/ratings/ranks/rank/0/@value", "statistics/ratings/ranks/rank/@value"], -1),
            averageRating=float(safeGet(bggDict, "statistics/ratings/average/@value", -1)),
            bggRating=float(safeGet(bggDict, "statistics/ratings/bayesaverage/@value", -1)),
            thumbnail=safeGet(bggDict, "thumbnail", "")
        )

    def getEmbed(self, flags: [str]) -> Embed:
        if self.bggId > 0:
            color = Color.dark_green()
            if self.copies_available >= 0:
                if self.copies_available == 0:
                    color = Color.red()
                else:
                    color = Color.green()
            embed = Embed(title=self.title, url=f"{BASE_URL}{self.bggId}", color=color)
        else:
            embed = Embed(title=self.title, color=Color.dark_green())

        embed.set_thumbnail(url=self.thumbnail)

        if "compact" not in flags:
            embed.add_field(name="Description", value=f"{unescape(self.description)}", inline=False)

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
            if self.learn_difficulty != Difficulty.UNDEFINED:
                embed.add_field(name="Learning difficulty", value=f"{self.learn_difficulty.name.lower()}", inline=True)
            if self.play_difficulty != Difficulty.UNDEFINED:
                embed.add_field(name="Playing difficulty", value=f"{self.play_difficulty.name.lower()}", inline=True)
        else:
            embed.add_field(name="Difficulty", value=f"{self.play_difficulty.name.lower()} / {self.learn_difficulty.name.lower()}", inline=True)

        if "compact" not in flags:
            embed.add_field(name="Rank", value=f"{self.rank if self.rank != -1 else "Not ranked"}", inline=True)

            if self.averageRating == -1.0:
                embed.add_field(name="Average Rating", value=f"Unknown", inline=True)
            else:
                embed.add_field(name="Average Rating", value=f"{self.averageRating}", inline=True)

            if self.bggRating == -1.0:
                embed.add_field(name="BGG Rating", value=f"Unknown", inline=True)
            else:
                embed.add_field(name="BGG Rating", value=f"{self.bggRating}", inline=True)

        if self.copies != -1:
            embed.add_field(name="Copies", value=f"{self.copies}", inline=True)
        if self.copies_available != -1:
            embed.add_field(name="Available Copies", value=f"{self.copies_available}", inline=True)

        return embed

    def getInsertQueries(self, nextID: int) -> ((str, list), (str, list)):
        queries = []
        self.id = nextID
        insertItemQuery = "INSERT INTO items (id, name, length, description, thumbnail, type, copies) VALUES (?, ?, ?, ?, ?, ?, ?);"
        insertItemArgs = [self.id, self.title, self.playingTime, self.description, self.thumbnail, "boardgame", self.copies]
        insertBoardGameQuery = "INSERT INTO boardgames (id, min_players, max_players, bgg_id, bgg_rating, bgg_average_rating, bgg_rank, learn_difficulty, play_difficulty) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"
        insertBoardGameArgs = [self.id, self.minPlayers, self.maxPlayers, self.bggId, self.bggRating, self.averageRating, self.rank, self.learn_difficulty.value, self.play_difficulty.value]
        queries.append((insertBoardGameQuery, insertBoardGameArgs))
        queries.append((insertItemQuery, insertItemArgs))
        for category in self.categories:
            insertCategoryQuery = "INSERT INTO categories (id, category) VALUES (?, ?);"
            insertCategoryArgs = [self.id, category]
            queries.append((insertCategoryQuery, insertCategoryArgs))
        return queries

    def getDict(self):
        return {
            "id": self.id,
            "name": self.title,
            "min_players": self.minPlayers,
            "max_players": self.maxPlayers,
            "playing_time": self.playingTime,
            "copies": self.copies,
            "available_copies": self.copies_available,
            "bgg_id": self.bggId,
            "description": self.description,
            "learn_difficulty": self.learn_difficulty.value,
            "play_difficulty": self.play_difficulty.value,
            "categories": self.categories,
            "bgg_rank": self.rank,
            "bgg_average_rating": self.averageRating,
            "bgg_rating": self.bggRating,
            "thumbnail": self.thumbnail
        }
