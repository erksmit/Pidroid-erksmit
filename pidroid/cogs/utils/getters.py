import discord

from typing import Optional

from pidroid.cogs.utils.aliases import GuildChannel

def get_role(guild: discord.Guild, role_id: Optional[int]) -> Optional[discord.Role]:
    if role_id is None:
        return None
    return guild.get_role(role_id)

def get_channel(guild: discord.Guild, channel_id: Optional[int]) -> Optional[GuildChannel]:
    if channel_id is None:
        return None
    return guild.get_channel(channel_id)


def setup(client):
    pass

def teardown(client):
    pass
