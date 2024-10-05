from enum import Enum

from disnake import Member, Embed, Color


class Difficulty(Enum):
    UNDEFINED = 0
    PARTY = 1
    EASY = 2
    NORMAL = 3
    HARD = 4
    CAMPAIGN = 5


class Platform(Enum):
    UNDEFINED = 0
    PC = 1
    PS4 = 2
    PS5 = 3
    XBOX = 4
    SWITCH = 5


def safeGet(dictionary: dict, paths: list[str] | str, default):
    if not isinstance(paths, list):
        paths = [paths]
    for path in paths:
        val = dictionary
        try:
            for key in path.split("/"):
                if isinstance(val, list):
                    val = val[int(key)]
                else:
                    val = val[key]
            return val
        except (KeyError, ValueError):
            continue
    return default


def getBorrowsListEmbed(borrows: list[dict], user: Member, current: bool):
    if user is not None:
        titleAppend: str = " by " + (user.nick if user.nick is not None else user.name)
    else:
        titleAppend = ""
    embed = Embed(title="Items borrowed" + titleAppend, color=Color.dark_gold())

    for entry in borrows:
        author = entry['user']
        returned = entry['returned'].strftime("%d/%m/%Y") if entry['returned'] is not None else "Not returned"
        retrieval_date = entry['retrieval_date'].strftime("%d/%m/%Y")
        itemType = entry['type'].value[:-1]
        if current and user:
            content = f"Retrieved: {retrieval_date}"
        elif not current and user:
            content = f"Retrieved: {retrieval_date}\nReturned: {returned}"
        elif current and not user:
            content = f"{author}\n{retrieval_date}"
        else:
            content = f"{author}\nRetrieved: {retrieval_date}\nReturned: {returned}"
        embed.add_field(name=f"{entry['name']} ({itemType})", value=content, inline=True)

    # Add empty fields to make the embed look better
    if len(borrows) < 9:
        for _ in range(9 - len(borrows)):
            embed.add_field(name="\u200b", value="\u200b", inline=True)
    return embed


def format_time(minutes):
    days = int(minutes // 1440)
    hours = int((minutes % 1440) // 60)
    mins = int(minutes % 60)
    seconds = int((minutes - int(minutes)) * 60)

    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if mins > 0:
        time_parts.append(f"{mins}m")
    if seconds > 0:
        time_parts.append(f"{seconds}s")
    return ' '.join(time_parts) if time_parts else '0m'


def getBorrowsStatsEmbed(borrows: list[dict], order: str):
    formatted = order + " borrows"
    if order == "time":
        formatted = "borrow time"
    embed = Embed(title=f"Borrow stats by {formatted}", color=Color.dark_gold())
    for count, entry in enumerate(borrows):
        displayName = f"**[{entry['rank']}]** {entry['user'].display_name}"
        embed.add_field(name=displayName, value=f"Total: {entry['total']}\nCurrent: {entry['current']}\nTime: {format_time(entry['time'])}", inline=True)
    return embed


def getBorrowItemStatsEmbed(borrow: list[dict], order: str):
    formatted = order + " borrows"
    if order == "time":
        formatted = "borrow time"
    elif order == "usertime":
        formatted = "longest borrow"
    embed = Embed(title=f"Borrow stats by {formatted}", color=Color.dark_gold())
    for count, entry in enumerate(borrow):
        embed.add_field(name=f"**[{entry['rank']}]** {entry['name']}", value=f"Total: {entry['total']}\nTime: {format_time(entry['time'])}\nLongest borrow: {format_time(entry['usertime'])} by {entry['user'].mention}", inline=True)
    return embed
