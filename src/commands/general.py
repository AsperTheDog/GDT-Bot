from disnake import ApplicationCommandInteraction, Permissions, Embed, Color
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

    @slash_command(name="ping", description="Simple command to test the bot", dm_permission=True)
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