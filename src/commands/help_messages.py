import json

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.modals import SendEmbedModal


class HelperMsgCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(name="sendembed", description="Send a custom embed message")
    @app_commands.describe(file="JSON file describing a full embed, used instead of the form")
    async def sendCustomEmbed(self, interaction: discord.Interaction, file: discord.Attachment = None):
        if file is None:
            await interaction.response.send_modal(SendEmbedModal(self.sendFormEmbed))
            return
        data = (await file.read()).decode('utf-8')
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            embed = discord.Embed(title="Error", description="The file must be a valid JSON file.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.send_message(embed=discord.Embed.from_dict(data))

    async def sendFormEmbed(self, interaction: discord.Interaction, modal: SendEmbedModal):
        colour = modal.colour.component.value.strip().lstrip("#").removeprefix("0x").removeprefix("0X")
        try:
            color = discord.Color(int(colour, 16)) if colour != "" else discord.Color.blurple()
        except ValueError:
            embed = discord.Embed(title="Error", description="The colour must be a hex value like #5865F2", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(title=modal.embed_title.component.value, description=modal.description.component.value, color=color)
        if modal.footer.component.value != "":
            embed.set_footer(text=modal.footer.component.value)
        if modal.image.component.value != "":
            embed.set_image(url=modal.image.component.value)
        try:
            await interaction.response.send_message(embed=embed)
        except discord.HTTPException as error:
            embed = discord.Embed(title="Error", description=str(error), color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
