import math
from http.client import HTTPException
from typing import Callable

import disnake
from disnake import Embed


class SuggestionPaginator(disnake.ui.View):
    def __init__(self, items: list):
        super().__init__(timeout=30)
        self.msg = None

        self.embed_index = 0
        self.embed = None
        self.items = items
        self.pages = math.ceil(len(items) / 9.0)
        self.createEmbed()

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = 0 == self.pages - 1
        self.last_page.disabled = 0 == self.pages - 1

    async def changeEmbed(self, interaction):
        self.createEmbed()

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

    def createEmbed(self):
        itemSlice = self.items[self.embed_index * 9: (self.embed_index * 9 + 9 if self.embed_index < self.pages - 1 else len(self.items))]
        string = ""
        for item in itemSlice:
            string += f"{item}\n"
        self.embed = Embed(title="Top Suggestions" if self.embed_index == 0 else "Suggestions", description=string, color=disnake.Color.blue())
        self.embed.set_footer(text="page {} of {}".format(self.embed_index + 1, self.pages))
