import json
import os
from dataclasses import dataclass

from disnake import ApplicationCommandInteraction, Permissions
from disnake.ext.commands import InteractionBot, CommandSyncFlags, slash_command

from database import DatabaseManager
from src.commands.general import GeneralCog
from src.commands.piazza import GamesCog

configFileName = "data_files/config.json"
databasePath = "data_files/database.sqlite"

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

    client.add_cog(GamesCog(client))
    client.add_cog(GeneralCog(client))

    client.run(data.token)


if __name__ == "__main__":
    main()
