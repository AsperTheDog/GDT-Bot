from functools import partial
from typing import Awaitable, Callable

import discord

from src.database import DBManager, ObjectType
from src.embed_helpers.common import Difficulty, Platform

DETAIL_ENUMS = {
    "play_difficulty": Difficulty,
    "learn_difficulty": Difficulty,
    "difficulty": Difficulty,
    "platform": Platform
}


class InsertBookModal(discord.ui.Modal, title="Insert a book"):
    book_title = discord.ui.Label(text="Title", component=discord.ui.TextInput(max_length=200, placeholder="The Art of War"))
    author = discord.ui.Label(text="Author", component=discord.ui.TextInput(max_length=200, placeholder="Sun Tzu"))
    pages = discord.ui.Label(text="Pages", component=discord.ui.TextInput(max_length=6, placeholder="273"))
    abstract = discord.ui.Label(text="Abstract", component=discord.ui.TextInput(style=discord.TextStyle.paragraph, required=False, max_length=1024))
    copies = discord.ui.Label(text="Copies", component=discord.ui.TextInput(default="1", max_length=3))

    def __init__(self, onSubmit: Callable[[discord.Interaction, 'InsertBookModal'], Awaitable[None]]):
        super().__init__()
        self.onSubmit = onSubmit

    async def on_submit(self, interaction: discord.Interaction):
        await self.onSubmit(interaction, self)


class InsertGameModal(discord.ui.Modal, title="Insert a game"):
    game_name = discord.ui.Label(text="Name", component=discord.ui.TextInput(max_length=200, placeholder="Ark Nova"))
    min_players = discord.ui.Label(text="Min players", component=discord.ui.TextInput(default="1", max_length=3))
    max_players = discord.ui.Label(text="Max players", component=discord.ui.TextInput(default="4", max_length=3))
    length = discord.ui.Label(text="Length (minutes)", component=discord.ui.TextInput(default="60", max_length=5))
    copies = discord.ui.Label(text="Copies", component=discord.ui.TextInput(default="1", max_length=3))

    def __init__(self, title: str, onSubmit: Callable[[discord.Interaction, 'InsertGameModal'], Awaitable[None]]):
        super().__init__(title=title)
        self.onSubmit = onSubmit

    async def on_submit(self, interaction: discord.Interaction):
        await self.onSubmit(interaction, self)


class DetailsModal(discord.ui.Modal):
    description = discord.ui.Label(text="Description", component=discord.ui.TextInput(style=discord.TextStyle.paragraph, required=False, max_length=1024))
    thumbnail = discord.ui.Label(text="Thumbnail URL", description="Submit empty to use the default image",
                                component=discord.ui.TextInput(required=False, max_length=512))
    categories = discord.ui.Label(text="Categories", description="Comma separated, submit empty to remove all of them",
                                 component=discord.ui.TextInput(required=False, max_length=512))

    def __init__(self, onSubmit: Callable[[discord.Interaction, 'DetailsModal'], Awaitable[None]], **defaults: str):
        super().__init__()
        self.onSubmit = onSubmit
        for name, value in defaults.items():
            getattr(self, name).component.default = value

    async def on_submit(self, interaction: discord.Interaction):
        await self.onSubmit(interaction, self)


class BoardgameDetailsModal(DetailsModal, title="Boardgame details"):
    play_difficulty = discord.ui.Label(text="Play difficulty", description="undefined, party, easy, normal, hard or campaign",
                                       component=discord.ui.TextInput(required=False, max_length=20))
    learn_difficulty = discord.ui.Label(text="Learn difficulty", description="undefined, party, easy, normal, hard or campaign",
                                        component=discord.ui.TextInput(required=False, max_length=20))


class VideogameDetailsModal(DetailsModal, title="Videogame details"):
    platform = discord.ui.Label(text="Platform", description="undefined, pc, ps4, ps5, xbox or switch",
                                component=discord.ui.TextInput(required=False, max_length=20))
    difficulty = discord.ui.Label(text="Difficulty", description="undefined, party, easy, normal, hard or campaign",
                                  component=discord.ui.TextInput(required=False, max_length=20))


class BookDetailsModal(DetailsModal, title="Book details"):
    pass


DETAIL_MODALS = {
    ObjectType.BOARDGAME: BoardgameDetailsModal,
    ObjectType.VIDEOGAME: VideogameDetailsModal,
    ObjectType.BOOK: BookDetailsModal
}


class DetailsView(discord.ui.View):
    def __init__(self, authorID: int, itemType: ObjectType, itemID: int, onApply: Callable[..., Awaitable[None]]):
        super().__init__(timeout=300)
        self.authorID = authorID
        self.itemType = itemType
        self.itemID = itemID
        self.onApply = onApply
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.authorID:
            await interaction.response.send_message("You are not allowed to click this button", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Add details", style=discord.ButtonStyle.blurple, row=0)
    async def addDetails(self, interaction: discord.Interaction, button: discord.ui.Button):
        entry = DBManager.getInstance().getItemData(self.itemType, self.itemID)
        if entry is None:
            await interaction.response.send_message("This item does not exist anymore", ephemeral=True)
            return
        defaults = {
            "description": entry.description,
            "thumbnail": entry.thumbnail,
            "categories": ", ".join(entry.categories)
        }
        if self.itemType is ObjectType.BOARDGAME:
            defaults["play_difficulty"] = entry.play_difficulty.name.lower()
            defaults["learn_difficulty"] = entry.learn_difficulty.name.lower()
        elif self.itemType is ObjectType.VIDEOGAME:
            defaults["platform"] = entry.platform.name.lower()
            defaults["difficulty"] = entry.difficulty.name.lower()
        await interaction.response.send_modal(DETAIL_MODALS[self.itemType](partial(self.onApply, self.itemType, self.itemID), **defaults))

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        try:
            await self.message.edit(view=None)
        except discord.HTTPException:
            pass


class SendEmbedModal(discord.ui.Modal, title="Send a custom embed"):
    embed_title = discord.ui.Label(text="Title", component=discord.ui.TextInput(max_length=256))
    description = discord.ui.Label(text="Description", component=discord.ui.TextInput(style=discord.TextStyle.paragraph, max_length=4000))
    colour = discord.ui.Label(text="Colour", component=discord.ui.TextInput(required=False, max_length=9, placeholder="#5865F2"))
    footer = discord.ui.Label(text="Footer", component=discord.ui.TextInput(required=False, max_length=2048))
    image = discord.ui.Label(text="Image URL", component=discord.ui.TextInput(required=False, max_length=512))

    def __init__(self, onSubmit: Callable[[discord.Interaction, 'SendEmbedModal'], Awaitable[None]]):
        super().__init__()
        self.onSubmit = onSubmit

    async def on_submit(self, interaction: discord.Interaction):
        await self.onSubmit(interaction, self)
