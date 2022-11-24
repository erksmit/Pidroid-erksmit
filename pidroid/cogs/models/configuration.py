from __future__ import annotations

from discord.channel import TextChannel
from discord.role import Role
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from pidroid.cogs.utils.api import API, GuildConfigurationTable

class GuildConfiguration:

    if TYPE_CHECKING:
        _id: int
        guild_id: int

        prefixes: List[str]

        jail_channel: Optional[int]
        jail_role: Optional[int]
        mute_role: Optional[int]
        log_channel: Optional[int]

        suggestion_channel: Optional[int]
        use_suggestion_threads: bool

        public_tags: bool

        suspicious_usernames: List[str]

    def __init__(self, api: API, data: GuildConfigurationTable) -> None:
        self.api = api
        self._deserialize(data)

    def _deserialize(self, c: GuildConfigurationTable) -> None:
        """Creates a GuildConfiguration object from a table object."""
        self._id = c.id # type: ignore
        self.guild_id = c.guild_id # type: ignore

        self.prefixes = c.prefixes # type: ignore

        self.jail_channel = c.jail_channel # type: ignore
        self.jail_role = c.jail_role # type: ignore
        self.mute_role = c.mute_role # type: ignore
        self.log_channel = c.log_channel # type: ignore
        
        self.suggestion_channel = c.suggestion_channel # type: ignore
        self.use_suggestion_threads = c.use_suggestion_threads  # type: ignore

        self.public_tags = c.public_tags # type: ignore

        self.suspicious_usernames = c.suspicious_usernames # type: ignore

    async def _update(self) -> None:
        await self.api.update_guild_configuration(
            self._id,
            self.jail_channel, self.jail_role,
            self.mute_role,
            self.log_channel,
            self.suggestion_channel,
            self.use_suggestion_threads,
            self.prefixes,
            self.suspicious_usernames,
            self.public_tags
        )

    async def update_public_tag_permission(self, allow_public: bool) -> None:
        """Updates public tag permission."""
        self.public_tags = allow_public
        await self._update()

    async def update_prefixes(self, prefix: str) -> None:
        """Updates the guild bot prefixes."""
        self.prefixes = [prefix]
        await self._update()

    async def update_jail_channel(self, channel: Optional[TextChannel]) -> None:
        """Updates the guild jail text channel."""
        if channel is None:
            self.jail_channel = None
        else:
            self.jail_channel = channel.id
        await self._update()

    async def update_jail_role(self, role: Optional[Role]) -> None:
        """Updates the guild jail role."""
        if role is None:
            self.jail_role = None
        else:
            self.jail_role = role.id
        await self._update()

    async def update_mute_role(self, role: Optional[Role]) -> None:
        """Updates the guild mute role."""
        if role is None:
            self.mute_role = None
        else:
            self.mute_role = role.id
        await self._update()

    async def update_log_channel(self, channel: Optional[TextChannel]) -> None:
        """Updates the guild log text channel."""
        if channel is None:
            self.log_channel = None
        else:
            self.log_channel = channel.id
        await self._update()

    async def update_suggestion_channel(self, channel: Optional[TextChannel]) -> None:
        """Updates the guild suggestion text channel."""
        if channel is None:
            self.suggestion_channel = None
        else:
            self.suggestion_channel = channel.id
        await self._update()

    async def update_suggestion_threads(self, use_threads: bool):
        """Updates use of suggestion threads."""
        self.use_suggestion_threads = use_threads
        await self._update()

    async def update_suspicious_users(self, suspicious_users: List[str]) -> None:
        """Updates the suspicious user list."""
        self.suspicious_usernames = suspicious_users
        await self._update()
