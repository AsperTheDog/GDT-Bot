import disnake
from disnake import HTTPException

from src.database import ObjectType


class ListPaginator(disnake.ui.View):
    def __init__(self, itemsType: ObjectType, items: [int], db):
        super().__init__(timeout=30)
        self.db = db
        self.msg = None

        self.items = items
        self.itemsType = itemsType
        self.embed_index = 0

    async def changeEmbed(self, interaction):
        raise NotImplementedError

    @disnake.ui.button(emoji="⏪", style=disnake.ButtonStyle.blurple, row=0)
    async def first_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_index = 0
        await self.changeEmbed(interaction)

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary, row=0)
    async def prev_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_index -= 1
        await self.changeEmbed(interaction)

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary, row=0)
    async def next_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_index += 1
        await self.changeEmbed(interaction)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.blurple, row=0)
    async def last_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_index = len(self.items) - 1
        await self.changeEmbed(interaction)

    async def on_timeout(self) -> None:
        await self.msg.edit(view=None)
