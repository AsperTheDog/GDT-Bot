import discord
from discord import app_commands
from discord.ext import commands

from src.bgg import BGGUnavailable, fetchBGGIDsFromName, fetchBGGameData
from src.utils.autocomplete import boardgameNameAutocomplete
from src.utils.paginator import ItemPaginator


class BoardGamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(name="fetchbgg", description="Fetch boardgame's information from BGG")
    @app_commands.describe(
        query="Name or BGG id of the boardgame",
        compact="Show a compact version of the embed",
        all_categories="Show every category instead of the first three",
        private="Only show the result to you")
    @app_commands.autocomplete(query=boardgameNameAutocomplete)
    async def fetchBoardgame(self, interaction: discord.Interaction, query: str, compact: bool = False, all_categories: bool = False, private: bool = True):
        await interaction.response.defer(ephemeral=private)

        if not self.bot.config.bggEnabled:
            embed = discord.Embed(title=f" Fetching Error", description=f"BoardGameGeek is disabled, use /bgsearch to browse the local collection", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        try:
            ids = await fetchBGGIDsFromName(query)
            if ids is None:
                ids = [int(query)]
            items = await fetchBGGameData(ids)
        except ValueError:
            embed = discord.Embed(title=f" Fetching Error", description=f"The game was not found in BGG", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        except BGGUnavailable:
            embed = discord.Embed(title=f" Fetching Error", description=f"BoardGameGeek is unavailable, use /bgsearch to browse the local collection", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        if len(items) == 0:
            embed = discord.Embed(title=f" Fetching Error", description=f"The game was not found in BGG", color=discord.Color.red())
            await interaction.edit_original_response(embed=embed)
            return
        flags = (["compact"] if compact else []) + (["allCats"] if all_categories else [])
        embed: discord.Embed = items[0].getEmbed(flags)
        view = ItemPaginator(items, flags, embed)
        embed.set_footer(text="Use arrows to move between pages")
        view.message = await interaction.original_response()
        await interaction.edit_original_response(embed=embed, view=view)
