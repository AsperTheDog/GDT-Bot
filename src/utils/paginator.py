import math
from typing import Awaitable, Callable

import discord

PAGE_SIZE = 9


def countPages(total: int, pageSize: int = PAGE_SIZE) -> int:
    return max(1, math.ceil(total / pageSize))


class LazyPaginator(discord.ui.View):
    def __init__(self, pages: int, loadPage: Callable[[int], Awaitable[discord.Embed]], timeout: float = 45):
        super().__init__(timeout=timeout)
        self.pages = max(1, pages)
        self.loadPage = loadPage
        self.page = 0
        self.message: discord.Message | None = None
        self.updateButtons()

    def updateButtons(self):
        firstPage = self.page == 0
        lastPage = self.page == self.pages - 1
        self.first_page.disabled = firstPage
        self.prev_page.disabled = firstPage
        self.next_page.disabled = lastPage
        self.last_page.disabled = lastPage

    async def changePage(self, interaction: discord.Interaction, page: int):
        self.page = min(max(page, 0), self.pages - 1)
        self.updateButtons()
        embed = await self.loadPage(self.page)
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.HTTPException as error:
            print(f"HTTP Exception: \n {str(error)}")

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.blurple, row=0)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.changePage(interaction, 0)

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.secondary, row=0)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.changePage(interaction, self.page - 1)

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.changePage(interaction, self.page + 1)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.blurple, row=0)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.changePage(interaction, self.pages - 1)

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        try:
            await self.message.edit(view=None)
        except discord.HTTPException:
            pass


class ItemPaginator(discord.ui.View):
    def __init__(self, items: list, flags: list[str], initialEmbed: discord.Embed):
        super().__init__(timeout=45)

        self.message: discord.Message | None = None
        self.items = items
        self.flags = flags
        self.embed_index: int = 0
        self.embed: discord.Embed = initialEmbed

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = 0 == len(self.items) - 1
        self.last_page.disabled = 0 == len(self.items) - 1

    async def changeEmbed(self, interaction: discord.Interaction):
        self.embed = self.items[self.embed_index].getEmbed(self.flags)
        self.embed.set_footer(text=f"Item {self.embed_index + 1} of {len(self.items)}")

        self.prev_page.disabled = self.embed_index == 0
        self.next_page.disabled = self.embed_index == len(self.items) - 1
        self.first_page.disabled = self.prev_page.disabled
        self.last_page.disabled = self.next_page.disabled
        try:
            await interaction.response.edit_message(embed=self.embed, view=self)
        except discord.HTTPException as error:
            print(f"HTTP Exception: \n {str(error)}")

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.blurple, row=0)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_index = 0
        await self.changeEmbed(interaction)

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.secondary, row=0)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_index -= 1
        await self.changeEmbed(interaction)

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_index += 1
        await self.changeEmbed(interaction)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.blurple, row=0)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed_index = len(self.items) - 1
        await self.changeEmbed(interaction)

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        try:
            await self.message.edit(view=None)
        except discord.HTTPException:
            pass
