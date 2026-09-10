import discord


async def botOwner(interaction: discord.Interaction) -> bool:
    return await interaction.client.is_owner(interaction.user)
