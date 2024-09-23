import requests
import xmltodict

from disnake import ApplicationCommandInteraction, Embed, Color
from disnake.ext.commands import Cog, slash_command

from src.bgg import fetchBGGameData
from src.embed_helpers.boardgame import BoardGameObj
from src.utils.paginator import BoardGamePaginator


class BoardGamesCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="fetchbgg", description="Fetch boardgame's information from BGG")
    async def fetchBoardgame(self, inter: ApplicationCommandInteraction, bgg_id: int):
        await inter.response.defer()

        game = fetchBGGameData([bgg_id])
        if not game:
            embed = Embed(title=f" Fetching Error", description=f"The game was not found in BGG", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        await self.__paginate(inter, game)

    async def __paginate(self, inter: ApplicationCommandInteraction, items: [BoardGameObj]):
        embed: Embed = items[0].getEmbed()
        if len(items) == 0:
            embed = Embed(title=f" Parsing Error", description=f"Parsing failed successfully", color=Color.red())
            await inter.edit_original_response(embed=embed)
        elif len(items) == 1:
            await inter.edit_original_response(embed=embed)
        else:
            view = BoardGamePaginator(items, embed)
            embed.set_footer(text="Use arrows to move between pages")
            view.msg = await inter.original_response()
            await view.msg.edit(embed=embed, view=view)
