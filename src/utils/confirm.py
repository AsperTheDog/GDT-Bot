from typing import Callable

import disnake
from disnake import HTTPException, Embed

from src.database import ObjectType, DBManager


class ConfirmDialog(disnake.ui.View):
    def __init__(self, initialEmbed, onConfirm: Callable[[], Embed], messageAuthor, labelYes="Yes", labelNo="No"):
        super().__init__(timeout=30)
        self.msgAuthor = messageAuthor
        self.embed: Embed = initialEmbed
        self.onConfirm = onConfirm
        self.confirm.label = labelYes
        self.cancel.label = labelNo

    async def changeEmbed(self, interaction: disnake.MessageInteraction, confirmed: bool):
        try:
            if confirmed:
                embed = self.onConfirm()
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                await interaction.response.edit_message(embed=Embed(title="Operation cancelled", color=disnake.Color.red()), view=None)
        except HTTPException as e:
            print("HTTP Exception: \n" + str(e))

    @disnake.ui.button(label="Yes", style=disnake.ButtonStyle.green, row=0)
    async def confirm(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.user.id != self.msgAuthor:
            await interaction.response.send_message("You are not allowed to click this button", ephemeral=True)
        await self.changeEmbed(interaction, True)

    @disnake.ui.button(label="No", style=disnake.ButtonStyle.red, row=0)
    async def cancel(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.user.id != self.msgAuthor:
            await interaction.response.send_message("You are not allowed to click this button", ephemeral=True)
        await self.changeEmbed(interaction, False)
