from dataclasses import dataclass
from html import unescape
from disnake import Embed, Color

from src.embed_helpers.common import Difficulty

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
            id=boardGameDict["id"] if "id" in boardGameDict else -1,
            title=boardGameDict["name"],
            minPlayers=boardGameDict["min_players"],
            maxPlayers=boardGameDict["max_players"],
            playingTime=boardGameDict["length"],
            copies=boardGameDict["copies"] if "copies" in boardGameDict else 0,
            copies_available=boardGameDict["available_copies"] if "available_copies" in boardGameDict else 0,
            bggId=boardGameDict["bgg_id"] if "bgg_id" in boardGameDict else -1,
            description=boardGameDict["description"] if "description" in boardGameDict else "No description available",
            learn_difficulty=boardGameDict["learn_difficulty"] if "learn_difficulty" in boardGameDict else Difficulty.UNDEFINED,
            play_difficulty=boardGameDict["play_difficulty"] if "play_difficulty" in boardGameDict else Difficulty.UNDEFINED,
            categories=boardGameDict["categories"] if "categories" in boardGameDict else [],
            rank=boardGameDict["bgg_rank"] if "bgg_rank" in boardGameDict else -1,
            averageRating=boardGameDict["bgg_average_rating"] if "bgg_average_rating" in boardGameDict else -1.0,
            bggRating=boardGameDict["bgg_rating"] if "bgg_rating" in boardGameDict else -1.0,
            thumbnail=boardGameDict["thumbnail"] if "thumbnail" in boardGameDict else "https://i.imgur.com/OJhoTqu.png"
        )

    @staticmethod
    def createFromBGG(bggDict: dict, extraData: dict = None):
        if isinstance(bggDict["@id"], str):
            bggDict["@id"] = int(bggDict["@id"])
        if extraData is None:
            extraData = {}
        name = ""
        if isinstance(bggDict["name"], list):
            name = bggDict["name"][0]["@value"]
        elif isinstance(bggDict["name"], dict):
            name = bggDict["name"]["@value"]
        if "play_difficulty" in extraData and isinstance(extraData["play_difficulty"], str):
            extraData["play_difficulty"] = Difficulty(int(extraData["play_difficulty"]))
        if "learn_difficulty" in extraData and isinstance(extraData["learn_difficulty"], str):
            extraData["learn_difficulty"] = Difficulty(int(extraData["learn_difficulty"]))
        return BoardGameObj(
            id=extraData["id"] if "id" in extraData else -1,
            title=name,
            minPlayers=bggDict["minplayers"]["@value"],
            maxPlayers=bggDict["maxplayers"]["@value"],
            playingTime=bggDict["playingtime"]["@value"],
            copies=extraData["copies"] if "copies" in extraData else -1,
            copies_available=extraData["available_copies"] if "available_copies" in extraData else -1,
            bggId=bggDict["@id"],
            description=bggDict["description"] if len(bggDict["description"]) < 1024 else bggDict["description"][:1020] + "...",
            learn_difficulty=extraData["learn_difficulty"] if "learn_difficulty" in extraData else Difficulty.UNDEFINED,
            play_difficulty=extraData["play_difficulty"] if "play_difficulty" in extraData else Difficulty.UNDEFINED,
            categories=[category["@value"] for category in bggDict["link"] if category["@type"] == "boardgamecategory"],
            rank=bggDict["statistics"]["ratings"]["ranks"]["rank"][0]["@value"]
            if isinstance(bggDict["statistics"]["ratings"]["ranks"]["rank"], list)
            else bggDict["statistics"]["ratings"]["ranks"]["rank"]["@value"],
            averageRating=bggDict["statistics"]["ratings"]["average"]["@value"],
            bggRating=bggDict["statistics"]["ratings"]["bayesaverage"]["@value"],
            thumbnail=bggDict["thumbnail"]
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
            embed.add_field(name="Learning difficulty", value=f"{self.learn_difficulty.name.lower()}", inline=True)
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
