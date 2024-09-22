import disnake
from disnake import HTTPException, Embed

from src.data_models.boardgamemodel import BoardGameModel
from src.database import ObjectType, DatabaseManager


class GamePaginator(disnake.ui.View):
    def __init__(self, itemsType: ObjectType, items: [int], extended: bool, initialEmbed: Embed, db: DatabaseManager):
        super().__init__(timeout=30)
        self.db = db

        self.itemsType = itemsType
        self.msg = None
        self.extended = extended
        self.items = items
        self.embed_index: int = 0
        self.embed: Embed = initialEmbed

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = 0 == len(self.items) - 1
        self.last_page.disabled = 0 == len(self.items) - 1

    async def changeEmbed(self, interaction: disnake.MessageInteraction):
        self.embed = self.db.getItemEmbed(self.itemsType, self.items[self.embed_index]['id'], self.extended)
        self.embed.set_footer(text="item {} of {}".format(self.embed_index + 1, len(self.items)))

        self.prev_page.disabled = self.embed_index == 0
        self.next_page.disabled = self.embed_index == len(self.items) - 1
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
        self.embed_index = len(self.items) - 1
        await self.changeEmbed(interaction)

    async def on_timeout(self) -> None:
        await self.msg.edit(view=None)

class BoardGamePaginator(disnake.ui.View):
    def __init__(self, items: [BoardGameModel], initialEmbed: Embed):
        super().__init__(timeout=45)

        self.msg = None
        self.items = items
        self.embed_index: int = 0
        self.embed: Embed = initialEmbed

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = 0 == len(self.items) - 1
        self.last_page.disabled = 0 == len(self.items) - 1

    async def changeEmbed(self, interaction: disnake.MessageInteraction):
        self.embed = self.items[self.embed_index].getEmbed()
        self.embed.set_footer(text=f"Item {self.embed_index + 1} of {len(self.items)}")

        self.prev_page.disabled = self.embed_index == 0
        self.next_page.disabled = self.embed_index == len(self.items) - 1
        self.first_page.disabled = self.prev_page.disabled
        self.last_page.disabled = self.next_page.disabled
        try:
            await interaction.response.edit_message(embed=self.embed, view=self)
        except HTTPException as e:
            print(f"HTTP Exception: \n {str(e)}")

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
