from disnake import ApplicationCommandInteraction, Permissions
from disnake.ext.commands import Cog, slash_command, InteractionBot


class GeneralCog(Cog):
    def __init__(self, bot):
        self.bot: InteractionBot = bot

    @slash_command(name="kill", description="Simple command to test the bot", default_member_permissions=Permissions(administrator=True))
    async def kill(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message("Shutting down...")
        print("Shutting down...")
        await self.bot.close()

    @slash_command(name="ping", description="Simple command to test the bot", default_member_permissions=Permissions(administrator=True))
    async def ping(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message("Pong!")
        print("Pong!")