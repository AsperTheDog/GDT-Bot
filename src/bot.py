import json
import os
from dataclasses import dataclass

from disnake import ApplicationCommandInteraction, Embed, Color
from disnake.ext.commands import InteractionBot, CommandSyncFlags, CommandError

from database import DatabaseManager
from src.commands.general import GeneralCog
from src.commands.piazza import GamesCog

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
            testGuilds=data["debug"]["testGuilds"]
        )


def initializeBot(bot: InteractionBot):
    print(f"Bot is ready as {bot.user}, configuring extra parameters...")
    bot.db = DatabaseManager(databasePath)
    print("Configuration finished")


def main():
    data: BotConfigData = configure()
    if data is None:
        return

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
        print(f"Error in command '{inter.application_command.name}' by {inter.author}: {error}")
        await inter.guild.system_channel.send(embed=embed)

    client.add_cog(GamesCog(client))
    client.add_cog(GeneralCog(client))

    client.run(data.token)


if __name__ == "__main__":
    main()
