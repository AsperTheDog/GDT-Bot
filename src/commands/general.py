import random

import discord
from discord import app_commands
from discord.ext import commands

from src.database import DBManager
from src.files import DATABASE_PATH, OTHER_DIR
from src.utils.checks import botOwner

RESULT_LIMIT = 4085


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @staticmethod
    def queryEmbed(statement: str) -> discord.Embed:
        success, result = DBManager.getInstance().execute(statement)
        if len(result) > RESULT_LIMIT:
            result = result[:RESULT_LIMIT - 3] + "..."
        if success:
            return discord.Embed(title="Query executed successfully", description=f"Result: {result}", color=discord.Color.green())
        return discord.Embed(title="Query failed", description=f"Error: {result}", color=discord.Color.red())

    @app_commands.command(name="kill", description="Simple command to test the bot")
    @app_commands.check(botOwner)
    async def kill(self, interaction: discord.Interaction):
        await interaction.response.send_message("Shutting down...")
        print("Shutting down...")
        await self.bot.close()

    @app_commands.command(name="ping", description="Simple command to test the bot")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")
        print("Pong!")

    @app_commands.command(name="executequery", description="Execute a custom query on the database")
    @app_commands.check(botOwner)
    async def executequery(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=GeneralCog.queryEmbed(query))

    @app_commands.command(name="executequeryfile", description="Execute a custom query on the database")
    @app_commands.check(botOwner)
    async def executequeryfile(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer()
        statement = (await file.read()).decode("utf-8")
        await interaction.edit_original_response(embed=GeneralCog.queryEmbed(statement))

    @app_commands.command(name="killallhumans", description="K, time to ill all humans")
    async def killallhumans(self, interaction: discord.Interaction):
        def getRandomLine(content: list[str], userid: int):
            isValid = False
            while not isValid:
                picked = random.choice(content)
                if picked.startswith("user:"):
                    isValid = self.bot.user_mapping.get(picked[5:].split("%")[0]) == userid
                    picked = picked[5:].split("%")[1]
                else:
                    isValid = True
            return picked

        with open(OTHER_DIR / "killallhumans.txt", "r", encoding="utf-8") as file:
            content: list[str] = file.read().split("\n")
        line = getRandomLine(content, interaction.user.id)
        if line.startswith("%EMBED%"):
            title, description, color = line[7:].split("%")
            embed = discord.Embed(title=title, description=description, color=discord.Color(int(color, 16)))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(line)

    @app_commands.command(name="getdb", description="Get the database")
    @app_commands.check(botOwner)
    async def getdb(self, interaction: discord.Interaction):
        await interaction.response.send_message(file=discord.File(DATABASE_PATH, filename="database.sqlite"))
