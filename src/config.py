import json
from dataclasses import dataclass, field

from src.files import CONFIG_PATH, EXAMPLE_CONFIG_PATH


@dataclass
class BotConfigData:
    token: str
    ownerIDs: list[int]
    syncCommandsDebug: bool
    testGuilds: list[int]
    errorLogsChannel: int
    bggEnabled: bool = True
    users: dict[str, int] = field(default_factory=dict)


def configure() -> BotConfigData | None:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Please configure the bot by editing '{CONFIG_PATH}'")
        return None
    data: dict = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return BotConfigData(
        token=data["security"]["token"],
        ownerIDs=data["security"].get("ownerIDs", []),
        syncCommandsDebug=data["debug"].get("syncCommandsDebug", False),
        testGuilds=data["debug"].get("testGuilds", []),
        errorLogsChannel=data["debug"].get("errorLogsChannel", 0),
        bggEnabled=data.get("features", {}).get("bgg", True),
        users=data.get("users", {})
    )
