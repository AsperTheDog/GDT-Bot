import json
import os
import sys
import traceback
from dataclasses import dataclass

from disnake import ApplicationCommandInteraction, Embed, Color
from disnake.ext.commands import InteractionBot, CommandSyncFlags, CommandError

from src.commands.help_messages import HelperMsgCog
from src.database import DBManager
from src.commands.general import GeneralCog
from src.commands.piazza import GamesCog
from src.commands.boardgamegeek import BoardGamesCog

configFileName = "data_files/config.json"
databasePath = "data_files/database.sqlite"

os.chdir(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class BotConfigData:
    # SECURITY
    token: str
    ownerIDs: [int]

    # DEBUG
    syncCommandsDebug: bool
    testGuilds: [int]
    errorLogsChannel: int

    users: dict = None


def configure() -> BotConfigData | None:
    if not os.path.exists(configFileName):
        with open(f"{configFileName}.example", "r") as example, open(configFileName, "w") as configFile:
            configFile.write(example.read())
        print(f"Please configure the bot by editing '{configFileName}'")
        return None
    with open(configFileName, "r") as configFile:
        data: dict = json.load(configFile)
        return BotConfigData(
            token=data["security"]["token"],
            ownerIDs=data["security"]["ownerIDs"],
            syncCommandsDebug=data["debug"]["syncCommandsDebug"],
            testGuilds=data["debug"]["testGuilds"],
            errorLogsChannel=data["debug"]["errorLogsChannel"],
            users=data["users"]
        )


def initializeBot(bot: InteractionBot):
    print(f"Bot is ready as {bot.user}")


def main():
    data: BotConfigData = configure()
    if data is None:
        return

    DBManager.initInstance(databasePath)

    client: InteractionBot = InteractionBot(
        command_sync_flags=CommandSyncFlags(sync_commands_debug=data.syncCommandsDebug),
        test_guilds=data.testGuilds
    )

    @client.event
    async def on_ready():
        initializeBot(client)

    @client.event
    async def on_slash_command_error(inter: ApplicationCommandInteraction, error: CommandError):
        embed = Embed(title="Error", description=str(error), color=Color.red())
        embed.add_field(name="Command", value=inter.application_command.name)
        embed.add_field(name="Arguments", value=str(inter.filled_options))
        embed.add_field(name="User", value=inter.author.mention)
        embed.add_field(name="Channel", value=inter.channel.mention)
        embed.set_footer(text=str(inter.created_at.strftime("%Y-%m-%d %H:%M:%S")))
        await inter.guild.get_channel(client.error_logs_channel).send(embed=embed)

        command = inter.application_command
        print(f"Ignoring exception in slash command {command.name!r}:", file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        msgEmbed = Embed(title="An error occurred", description="An error occurred while processing your command, developers have been notified. Heads will roll...", color=Color.red())
        await inter.edit_original_response(embed=msgEmbed)

    client.add_cog(GamesCog(client))
    client.add_cog(GeneralCog(client))
    client.add_cog(BoardGamesCog(client))
    client.add_cog(HelperMsgCog(client))
    client.error_logs_channel = data.errorLogsChannel
    client.userMapping = data.users

    client.run(data.token)


if __name__ == "__main__":
    main()
