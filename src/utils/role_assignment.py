import disnake
from disnake.ext import commands

class ReactionRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_id = 1 #servers id
        self.message_id_to_watch = 1 # pinned message id

        self.emoji_role_map = {
            # program student
            ":piñata:": 1252675171236450418,
            # course student
            ":microbe:": 1279758745290936330,
            # friends of the show
            ":roller_skate:": 1252675234599927879,
            #alumn
            ":older_adult:" : 1280503321806770289
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        if payload.message_id != self.message_id_to_watch:
            return

        emoji = str(payload.emoji)
        role_id = self.emoji_role_map.get(emoji)
        if not role_id:
            return  # ignore all other emojis

        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        # Check if user already has ANY of the reaction roles
        already_has_role = any(guild.get_role(rid) in member.roles for rid in self.emoji_role_map.values())
        if already_has_role:
            return  #user already claimed a role, skip

        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role, reason="Reaction role chosen")
            print(f"Assigned role {role.name} to {member.display_name}")
