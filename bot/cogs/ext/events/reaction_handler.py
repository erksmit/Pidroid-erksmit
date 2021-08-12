import discord

from discord.channel import TextChannel
from discord.ext import commands
from discord.message import Message
from discord.raw_models import RawReactionActionEvent

from client import Pidroid
from constants import JUSTANYONE_ID, SPOILERS_CHANNEL, SUGGESTIONS_CHANNEL
from cogs.utils.checks import is_client_pidroid, is_theotown_guild

class ReactionEventHandler(commands.Cog):
    """This class implements a cog for handling of events related to reactions."""
    def __init__(self, client: Pidroid):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not is_client_pidroid(self.client):
            return

        if message.author.bot:
            return

        if not message.guild or not is_theotown_guild(message.guild):
            return

        if message.channel.id == SPOILERS_CHANNEL:
            await message.add_reaction(emoji="<:bear_think:431390001721376770>")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if not is_client_pidroid(self.client):
            return

        member: discord.Member = payload.member
        channel: TextChannel = self.client.get_channel(payload.channel_id)
        try:
            message: Message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if not message:
            return

        # Remove suggestions via reaction
        if channel.id == SUGGESTIONS_CHANNEL and member.id == JUSTANYONE_ID and str(payload.emoji) == "⛔":
            await message.delete(delay=0)


def setup(client: Pidroid) -> None:
    client.add_cog(ReactionEventHandler(client))