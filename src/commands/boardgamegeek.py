import requests
import xmltodict

from disnake import ApplicationCommandInteraction, Embed, Color
from disnake.ext.commands import Cog, slash_command

from src.bgg import fetchBGGameData, fetchBGGIDsFromName
from src.embed_helpers.boardgame import BoardGameObj
from src.utils.paginator import ItemPaginator


class BoardGamesCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="fetchbgg", description="Fetch boardgame's information from BGG")
    async def fetchBoardgame(self, inter: ApplicationCommandInteraction, query: str, flags: str = ""):
        await inter.response.defer()

        ids = fetchBGGIDsFromName(query)
        print(ids)
        if ids is None:
            try:
                ids = [int(query)]
            except ValueError:
                embed = Embed(title=f" Fetching Error", description=f"The game was not found in BGG", color=Color.red())
                await inter.edit_original_response(embed=embed)
                return

        items = fetchBGGameData(ids)
        if len(items) == 0:
            embed = Embed(title=f" Fetching Error", description=f"The game was not found in BGG", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        flags = [flag.strip() for flag in flags.split(",")]
        embed: Embed = items[0].getEmbed(flags)
        if len(items) == 0:
            embed = Embed(title=f" Parsing Error", description=f"Parsing failed successfully", color=Color.red())
            await inter.edit_original_response(embed=embed)
        else:
            view = ItemPaginator(items, flags, embed)
            embed.set_footer(text="Use arrows to move between pages")
            view.msg = await inter.original_response()
            await view.msg.edit(embed=embed, view=view)
