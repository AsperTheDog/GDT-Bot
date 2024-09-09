from http.client import HTTPException

import disnake
from disnake import Embed

from src.database import DatabaseManager


class BorrowPaginator(disnake.ui.View):
    def __init__(self, size: int, initialEmbed: Embed, db: DatabaseManager, user: int = None):
        super().__init__(timeout=30)
        self.db = db
        self.msg = None

        self.embed_index = 0
        self.pages = size
        self.user = user
        self.embed: Embed = initialEmbed

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = 0 == self.pages - 1
        self.last_page.disabled = 0 == self.pages - 1

    async def changeEmbed(self, interaction):
        start = self.embed_index * 10
        end = start + 10
        self.embed = await self.db.getBorrowsListEmbed((start, end), interaction, self.user)
        self.embed.set_footer(text="page {} of {}".format(self.embed_index + 1, self.pages))

        self.prev_page.disabled = self.embed_index == 0
        self.next_page.disabled = self.embed_index == self.pages - 1
        self.first_page.disabled = self.prev_page.disabled
        self.last_page.disabled = self.next_page.disabled

        try:
            await interaction.response.edit_message(embed=self.embed, view=self)
        except HTTPException as e:
            print("HTTP Exception: \n" + str(e))

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
        self.embed_index = self.pages - 1
        await self.changeEmbed(interaction)

    async def on_timeout(self) -> None:
        await self.msg.edit(view=None)
