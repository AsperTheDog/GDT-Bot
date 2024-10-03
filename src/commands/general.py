import random

from disnake import ApplicationCommandInteraction, Embed, Color, File, Attachment
from disnake.ext.commands import Cog, slash_command, InteractionBot

from src.database import DBManager


class GeneralCog(Cog):
    def __init__(self, bot):
        self.bot: InteractionBot = bot

    @slash_command(name="kill", description="Simple command to test the bot")
    async def kill(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message("Shutting down...")
        print("Shutting down...")
        await self.bot.close()

    @slash_command(name="ping", description="Simple command to test the bot")
    async def ping(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message("Pong!")
        print("Pong!")

    @slash_command(name="executequery", description="Execute a custom query on the database")
    async def executequery(self, inter: ApplicationCommandInteraction, query: str):
        await inter.response.defer()
        success, result = DBManager.getInstance().execute(query)
        if len(result) > 4085:
            result = result[:4082] + "..."
        if success:
            embed = Embed(title="Query executed successfully", description=f"Result: {result}", color=Color.green())
        else:
            embed = Embed(title="Query failed", description=f"Error: {result}", color=Color.red())
        await inter.edit_original_response(embed=embed)

    @slash_command(name="executequeryfile", description="Execute a custom query on the database")
    async def executequeryfile(self, inter: ApplicationCommandInteraction, file: Attachment):
        await inter.response.defer()
        data = (await file.read()).decode('utf-8')
        success, result = DBManager.getInstance().execute(data)
        if len(result) > 4085:
            result = result[:4082] + "..."
        if success:
            embed = Embed(title="Query executed successfully", description=f"Result: {result}", color=Color.green())
        else:
            embed = Embed(title="Query failed", description=f"Error: {result}", color=Color.red())
        await inter.edit_original_response(embed=embed)


    @slash_command(name="killallhumans", description="K, time to ill all humans")
    async def killallhumans(self, inter: ApplicationCommandInteraction):
        def getRandomLine(content: [str], userid: int):
            isValid = False
            while not isValid:
                picked = random.choice(content)
                if picked.startswith("user:"):
                    isValid = self.bot.userMapping[picked[5:].split("%")[0]] == userid
                    picked = picked[5:].split("%")[1]
                else:
                    isValid = True
            return picked

        with open("data_files/other/killallhumans.txt", "r") as file:
            content: [str] = file.read().split("\n")
        line = getRandomLine(content, inter.author.id)
        if line.startswith("%EMBED%"):
            title, description, color = line[7:].split("%")
            embed = Embed(title=title, description=description, color=Color(int(color, 16)))
            await inter.response.send_message(embed=embed)
        else:
            await inter.response.send_message(line)

    @slash_command(name="getdb", description="Get the database")
    async def getdb(self, inter: ApplicationCommandInteraction):
        with open("data_files/database.sqlite", "rb") as file:
            await inter.response.send_message(file=File(file, filename="database.sqlite"))
