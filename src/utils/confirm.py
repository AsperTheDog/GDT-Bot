from typing import Callable

import discord


class ConfirmView(discord.ui.View):
    def __init__(self, messageAuthor: int, embed: discord.Embed, onConfirm: Callable[[], discord.Embed], labelYes="Yes", labelNo="No"):
        super().__init__(timeout=30)
        self.msgAuthor = messageAuthor
        self.embed = embed
        self.onConfirm = onConfirm
        self.confirm.label = labelYes
        self.cancel.label = labelNo
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.msgAuthor:
            await interaction.response.send_message("You are not allowed to click this button", ephemeral=True)
            return False
        return True

    async def changeEmbed(self, interaction: discord.Interaction, confirmed: bool):
        if confirmed:
            embed = await discord.utils.maybe_coroutine(self.onConfirm)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(embed=discord.Embed(title="Operation cancelled", color=discord.Color.red()), view=None)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green, row=0)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.changeEmbed(interaction, True)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red, row=0)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.changeEmbed(interaction, False)

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        try:
            await self.message.edit(view=None)
        except discord.HTTPException:
            pass
