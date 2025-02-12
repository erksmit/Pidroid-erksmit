from discord import (
    CategoryChannel, ForumChannel, StageChannel, TextChannel, Thread, VoiceChannel, DMChannel, GroupChannel, PartialMessageable,
    Member, User
)

from typing import Union
from typing_extensions import TypeAlias

GuildChannel: TypeAlias = Union[TextChannel, VoiceChannel, CategoryChannel, StageChannel, Thread, ForumChannel]
AllChannels: TypeAlias = Union[TextChannel, VoiceChannel, CategoryChannel, StageChannel, Thread, ForumChannel, DMChannel, GroupChannel, PartialMessageable]
                            
GuildTextChannel = Union[TextChannel, Thread]
DiscordUser: TypeAlias = Union[Member, User]
