import json

from disnake import ApplicationCommandInteraction, Permissions, Embed, Attachment, Color
from disnake.ext.commands import Cog, slash_command, InteractionBot


class HelperMsgCog(Cog):
    def __init__(self, bot):
        self.bot: InteractionBot = bot

    @slash_command(name="sendembed", description="Send a custom embed message", default_member_permissions=Permissions(administrator=True))
    async def sendCustomEmbed(self, inter: ApplicationCommandInteraction, file: Attachment):
        await inter.response.defer()
        data = (await file.read()).decode('utf-8')
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            embed = Embed(title="Error", description="The file must be a valid JSON file.", color=Color.red())
            await inter.edit_original_response(embed=embed)
            return
        embed = Embed.from_dict(data)
        await inter.delete_original_message()
        await inter.channel.send(embed=embed)
