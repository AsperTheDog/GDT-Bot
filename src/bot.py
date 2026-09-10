import logging
import sys
import traceback
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import discord
from discord import app_commands
from discord.ext import commands

from src.commands.boardgamegeek import BoardGamesCog
from src.commands.general import GeneralCog
from src.commands.help_messages import HelperMsgCog
from src.commands.piazza import GamesCog
from src.commands.suggestions import SuggestionsCog
from src.config import BotConfigData, configure
from src.database import DBManager
from src.files import DATABASE_PATH


def initializeBot(bot: commands.Bot):
    print(f"Bot is ready as {bot.user}")


class GDTBot(commands.Bot):
    def __init__(self, config: BotConfigData):
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default(),
                         owner_ids=set(config.ownerIDs), help_command=None)
        self.config = config
        self.user_mapping = config.users

    async def setup_hook(self):
        if self.config.syncCommandsDebug:
            logging.getLogger("discord.app_commands").setLevel(logging.DEBUG)
        database = DBManager(str(DATABASE_PATH))
        if database.needsPopulating:
            await database.populateDefaultData(self.config.bggEnabled)
        await self.add_cog(GamesCog(self))
        await self.add_cog(GeneralCog(self))
        await self.add_cog(BoardGamesCog(self))
        await self.add_cog(HelperMsgCog(self))
        await self.add_cog(SuggestionsCog(self))
        self.tree.on_error = self.onAppCommandError
        await self.syncCommands()

    async def syncCommands(self):
        for guildID in self.config.testGuilds:
            guild = discord.Object(id=guildID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced commands to test guild {guildID}")
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands globally")

    async def on_ready(self):
        initializeBot(self)

    async def close(self):
        await super().close()
        if DBManager.instance is not None:
            DBManager.instance.close()

    @staticmethod
    async def respondError(interaction: discord.Interaction, embed: discord.Embed):
        try:
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            pass

    async def onAppCommandError(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        command = interaction.command
        if isinstance(error, app_commands.CheckFailure):
            embed = discord.Embed(title="Error", description="You are not allowed to use this command", color=discord.Color.red())
            await GDTBot.respondError(interaction, embed)
            return

        options = interaction.data.get("options", []) if isinstance(interaction.data, dict) else []
        arguments = ", ".join(f"{option['name']}: {option.get('value')}" for option in options) if len(options) > 0 else "None"
        embed = discord.Embed(title="Error", description=str(error), color=discord.Color.red())
        embed.add_field(name="Command", value=command.qualified_name if command is not None else "Unknown")
        embed.add_field(name="Arguments", value=arguments)
        embed.add_field(name="User", value=interaction.user.mention)
        embed.add_field(name="Channel", value=getattr(interaction.channel, "mention", "Unknown"))
        embed.set_footer(text=interaction.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        channel = self.get_channel(self.config.errorLogsChannel)
        if channel is not None:
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

        print(f"Ignoring exception in slash command {command.name if command is not None else 'unknown'!r}:", file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        msgEmbed = discord.Embed(title="An error occurred", description="An error occurred while processing your command, developers have been notified. Heads will roll...", color=discord.Color.red())
        await GDTBot.respondError(interaction, msgEmbed)


def main():
    data: BotConfigData = configure()
    if data is None:
        return

    client: GDTBot = GDTBot(data)
    client.run(data.token)


if __name__ == "__main__":
    main()
