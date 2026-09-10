import discord
from discord import app_commands
from rapidfuzz import fuzz

from src.database import DBManager, ObjectType

MAX_CHOICES = 25
ITEM_SIMILARITY_THRESHOLD = 70


def itemChoices(entries: list[dict]) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=entry['name'][:100], value=str(entry['id'])) for entry in entries[:MAX_CHOICES]]


def nameChoices(names: list[str]) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=name[:100], value=name) for name in names[:MAX_CHOICES]]


def similarItems(current: str, limit: int = MAX_CHOICES, threshold: float = ITEM_SIMILARITY_THRESHOLD, itemType: ObjectType = None) -> list[dict]:
    if current == "":
        return DBManager.getInstance().searchItems(limit=limit, itemType=itemType)
    matches = DBManager.getInstance().searchItems(current, itemType)
    found = {entry['id'] for entry in matches}
    scored = [(fuzz.partial_ratio(entry['name'], current), entry) for entry in DBManager.getInstance().searchItems(itemType=itemType) if entry['id'] not in found]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return (matches + [entry for score, entry in scored if score >= threshold])[:limit]


async def itemAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().searchItems(current))


async def borrowableAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().getItemsToBorrowFromName(interaction.user.id, current))


async def returnableAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().getItemsToReturnFromName(interaction.user.id, current))


async def interestAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().getUserInterests(interaction.user.id, current))


async def suggestionAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return nameChoices(DBManager.getInstance().getSuggestionNames(search=current, limit=MAX_CHOICES))


async def similarItemAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return nameChoices([entry['name'] for entry in similarItems(current)])


async def boardgameAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().searchItems(current, ObjectType.BOARDGAME))


async def videogameAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().searchItems(current, ObjectType.VIDEOGAME))


async def bookAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return itemChoices(DBManager.getInstance().searchItems(current, ObjectType.BOOK))


async def boardgameNameAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return nameChoices([entry['name'] for entry in similarItems(current, itemType=ObjectType.BOARDGAME)])


async def videogameNameAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return nameChoices([entry['name'] for entry in similarItems(current, itemType=ObjectType.VIDEOGAME)])


async def bookNameAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return nameChoices([entry['name'] for entry in similarItems(current, itemType=ObjectType.BOOK)])


async def bookAuthorAutocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return nameChoices(DBManager.getInstance().getBookAuthors(current, MAX_CHOICES))
