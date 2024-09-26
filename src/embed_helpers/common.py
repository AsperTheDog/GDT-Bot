from enum import Enum

from disnake import Member, Embed, ApplicationCommandInteraction, Color


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
            content = f"**Retrieved at:** {retrieval_date}"
        elif not current and user:
            content = f"**Retrieved at:** {retrieval_date}\n**Returned at:** {returned}"
        elif current and not user:
            content = f"**User:** {author}\n**Retrieved at:** {retrieval_date}"
        else:
            content = f"**User:** {author}\n**Retrieved at:** {retrieval_date}\n**Returned at:** {returned}"
        embed.add_field(name=f"{entry['name']} ({itemType})", value=content, inline=True)

    # Add empty fields to make the embed look better
    if len(borrows) < 9:
        for _ in range(9 - len(borrows)):
            embed.add_field(name="\u200b", value="\u200b", inline=True)
    return embed