from html import unescape
from disnake import Embed, Color

class BoardGameModel:
    BASE_URL = f'://boardgamegeek.com/boardgame/'

    def __init__(self, gameId: str, title: str, thumbnail: str, image: str, description: str, minPlayers: str,
                 maxPlayers: str, playingTime: str, categories: str, rank: str, averageRating: str, bggRating: str,
                 tags: str
    ):
        self.gameId = gameId
        self.title = title
        self.thumbnail = thumbnail
        self.image = image
        self.description = description
        self.minPlayers = minPlayers
        self.maxPlayers = maxPlayers
        self.playingTime = playingTime
        self.categories = categories
        self.rank = rank
        self.averageRating = averageRating
        self.bggRating = bggRating
        self.tags = tags

    def getEmbed(self) -> Embed:
        embed = Embed(title=self.title, url=f"{self.BASE_URL}{self.gameId}",
                      color=Color.dark_green())
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(name="Description", value=f"{unescape(self.description)}", inline=False)
        embed.add_field(name="Categories", value=f"{self.categories}", inline=True)
        embed.add_field(name="Players", value=f"{self.minPlayers} - {self.maxPlayers}", inline=True)
        embed.add_field(name="Playing Time", value=f"{self.playingTime} minutes", inline=True)
        embed.add_field(name="Rank", value=f"{self.rank}", inline=True)
        embed.add_field(name="Average Rating", value=f"{self.averageRating}", inline=True)
        embed.add_field(name="BGG Rating", value=f"{self.bggRating}", inline=True)
        embed.add_field(name="Tags", value=f"{self.tags}", inline=False)
        return embed