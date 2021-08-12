from __future__ import annotations

import bson
import motor.motor_asyncio
import random
import secrets
import string

from bson.objectid import ObjectId
from discord.ext.commands.errors import BadArgument
from typing import List, Union, TYPE_CHECKING
from urllib.parse import quote_plus

from cogs.models.plugins import NewPlugin, Plugin
from cogs.utils.http import get, Route
from cogs.utils.time import utcnow

if TYPE_CHECKING:
    from client import Pidroid

class API:
    """This class handles actions related to Pidroid Mongo database calls."""

    def __init__(self, client: Pidroid, connection_string: str):
        self.client = client
        self.db_client = motor.motor_asyncio.AsyncIOMotorClient(connection_string, serverSelectionTimeoutMS=5000)
        self.db = self.db_client["Pidroid"]

    async def get(self, route: Route) -> dict:
        "Sends a GET request to TheoTown API."
        async with await get(self.client, route.url, route.headers) as r:
            return await r.json()

    @staticmethod
    def generate_id(characters: str = string.ascii_lowercase + string.ascii_uppercase + string.digits, size: int = 6) -> str:
        """Generates a cryptographically secure string of random digits and letters."""
        return ''.join(secrets.choice(characters) for _ in range(size))

    async def is_id_unique(self, collection: str, g_id: str) -> bool:
        """Returns True if current ID is not used."""
        return await self.db[collection].find_one({"id": g_id}) is None

    async def get_unique_id(self, collection: str) -> str:
        """Returns a unique ID."""
        failed_count = 0
        g_id = API.generate_id()
        while not await self.is_id_unique(collection, g_id):
            failed_count += 1
            if failed_count > 15:
                # This is when you are really screwed
                raise BadArgument("Mongo was unable to generate a unique ID after trying 15 times")
            g_id = API.generate_id()
        return g_id

    """Suggestion related methods"""

    async def submit_suggestion(self, author_id: int, message_id: int, suggestion: str, attachment_url: str = None) -> str:
        """Submits suggestion to the database. Returns suggestion ID."""
        g_id = await self.get_unique_id("Suggestions")
        d = {
            "id": g_id,
            "author": bson.Int64(author_id),
            "message_id": bson.Int64(message_id),
            "suggestion": suggestion,
            "timestamp": bson.Int64(utcnow().timestamp())
        }
        if attachment_url:
            d["attachment_url"] = attachment_url
        await self.db["Suggestions"].insert_one(d)
        return g_id

    """Plugin API related methods"""

    async def get_new_plugins(self, last_approval_time: int) -> List[NewPlugin]:
        """Queries the TheoTown API for new plugins after the specified approval time."""
        response = await self.get(Route("/private/get_new_plugins", {"last_approval_time": last_approval_time}))
        return [NewPlugin(np) for np in response["data"]]

    async def find_plugin(self, query: str, show_hidden: bool = False, narrow_search: bool = False) -> List[Plugin]:
        """Queries the TheoTown API for plugins matching the query string."""
        response = await self.get(Route(
            "/private/plugin/find",
            {"query": quote_plus(query.replace('#', '')), "show_hidden": show_hidden, "narrow": narrow_search}
        ))
        return [Plugin(p) for p in response["data"]]

    async def create_new_plugin_thread(self, thread_id: int, expires: int) -> None:
        await self.db["Plugin_threads"].insert_one({
            "thread_id": thread_id,
            "expires": expires
        })

    async def get_archived_plugin_threads(self, time: float) -> list:
        """Returns a list of active plugin threads which require to be archived."""
        cursor = self.db["Plugin_threads"].find(
            {"expires": {"$lte": time}}
        )
        return [i async for i in cursor]

    async def remove_plugin_thread_record(self, _id: ObjectId) -> None:
        await self.db["Plugin_threads"].delete_many({"_id": _id})

    """Moderation related methods"""

    async def create_punishment(
        self, punishment_type: str, guild_id: int,
        user_id: int, user_name: str,
        moderator_id: int, moderator_name: str,
        issued: int, reason: str, expiration: int = -1
    ) -> str:
        """Creates a punishment entry in the database. Retuns case ID."""
        g_id = await self.get_unique_id("Punishments")
        d = {
            "id": g_id,
            "type": punishment_type,
            "guild_id": bson.Int64(guild_id),
            "user_id": bson.Int64(user_id),
            "user_name": user_name,
            "moderator_id": bson.Int64(moderator_id),
            "moderator_name": moderator_name,
            "reason": reason,
            "date_issued": issued,
            "date_expires": expiration,
            "visible": True
        }
        await self.db["Punishments"].insert_one(d)
        return g_id

    async def get_case(self, case_id: str) -> Union[dict, None]:
        """Returns specified case information."""
        return await self.db["Punishments"].find_one({"id": str(case_id), "visible": True})

    async def get_guild_case(self, guild_id: int, case_id: str):
        """Returns specified guild case information."""
        return await self.db["Punishments"].find_one({"id": str(case_id), "guild_id": guild_id, "visible": True})

    async def get_active_warnings(self, guild_id: int, user_id: int) -> list:
        """Returns all active warnings for the specified user."""
        cursor = self.db["Punishments"].find({
            "type": "warning",
            "guild_id": guild_id,
            "user_id": user_id,
            "date_expires": {"$gte": int(utcnow().timestamp())},
            "visible": True
        }).sort("date_issued", -1)
        return [i async for i in cursor]

    async def get_all_warnings(self, guild_id: int, user_id: int) -> list:
        """Returns all warnings for the specified user."""
        cursor = self.db["Punishments"].find(
            {"type": "warning", "guild_id": guild_id, "user_id": user_id, "visible": True},
        ).sort("date_issued", -1)
        return [i async for i in cursor]

    async def get_moderation_logs(self, guild_id: int, user_id: int) -> list:
        """Returns all moderation logs for the specified user."""
        cursor = self.db["Punishments"].find(
            {"guild_id": guild_id, "user_id": user_id, "visible": True},
        ).sort("date_issued", -1)
        return [i async for i in cursor]

    async def update_case_reason(self, case_id: int, reason: str) -> None:
        """Updates case reason."""
        await self.db["Punishments"].update_one(
            {'id': case_id},
            {'$set': {'reason': reason}}
        )

    async def invalidate_case(self, case_id: int) -> None:
        """Invalidates a case by the specified ID by making it expired and hiding it."""
        await self.db["Punishments"].update_one(
            {'id': case_id},
            {'$set': {'date_expires': 0, "visible": False}}
        )

    async def revoke_punishment(self, punishment_type: str, guild_id: int, user_id: int) -> None:
        """Revokes specified punishment by making it expired."""
        await self.db["Punishments"].update_many(
            {'type': punishment_type, 'guild_id': guild_id, 'user_id': user_id},
            {'$set': {'date_expires': 0}}
        )

    async def get_moderation_statistics(self, guild_id: int, moderator_id: int) -> tuple:
        """Returns general moderation statistics of the specified guild and member."""
        cursor = self.db["Punishments"].find(
            {"guild_id": guild_id, "moderator_id": moderator_id, "visible": True}
        )
        moderator_data = [i async for i in cursor]

        guild_total = await self.db["Punishments"].count_documents(
            {"guild_id": guild_id, "visible": True}
        )
        return moderator_data, guild_total

    async def is_currently_jailed(self, guild_id: int, user_id: int) -> bool:
        """Returns true if member is currently jailed."""
        count = await self.db["Punishments"].count_documents(
            {"type": "jail", "guild_id": guild_id, "user_id": user_id, "date_expires": {"$ne": 0}, "visible": True}
        )
        return count > 0

    async def is_currently_muted(self, guild_id: int, user_id: int) -> bool:
        """Returns true if member is currently muted."""
        count = await self.db["Punishments"].count_documents(
            {"type": "mute", "guild_id": guild_id, "user_id": user_id, "date_expires": {"$ne": 0}, "visible": True}
        )
        return count > 0

    async def has_punishment_expired(self, punishment_type: str, guild_id: int, user_id: int) -> bool:
        """Returns true if the specified punishment should be carried over for the specified user according to the current time."""

        r = await self.db["Punishments"].find_one(
            {"type": punishment_type, "guild_id": guild_id, "user_id": user_id, "date_expires": {"$ne": 0}, "visible": True},
            {"date_expires": -1}
        )

        if r is None:
            return True

        expire = r["date_expires"]
        return expire < int(utcnow().timestamp()) and expire != 1

    async def get_active_guild_punishments(self, guild_id: int) -> list:
        """Returns a list of active punishments. NOTE that this excludes as they are not considered active."""
        cursor = self.db["Punishments"].find(
            {"type": {"$ne": "warning"}, "guild_id": guild_id, "date_expires": {"$gt": 0}, "visible": True}
        )
        return [i async for i in cursor]

    """Guild configuration related methods"""

    async def get_all_guild_configurations(self) -> Union[list, None]:
        """Returns a list of all guild configurations."""
        cursor = self.db["Guild_configurations"].find({})
        return [i async for i in cursor] or None

    async def get_guild_configuration(self, guild_id: int) -> Union[dict, None]:
        """Returns a specified guild configuration."""
        return await self.db["Guild_configurations"].find_one({"guild_id": guild_id})

    async def create_new_guild_configuration(
        self, guild_id: int,
        jail_id: int = None, jail_role_id: int = None,
        mute_role_id: int = None
    ) -> None:
        """Creates a new guild configuration entry."""
        d = {
            "guild_id": bson.Int64(guild_id),
        }
        if jail_id:
            d["jail_channel"] = bson.Int64(jail_id)
        if jail_role_id:
            d["jail_role"] = bson.Int64(jail_role_id)
        if mute_role_id:
            d["mute_role"] = bson.Int64(mute_role_id)
        await self.db["Guild_configurations"].insert_one(d)

    async def update_guild_jail_channel(self, guild_id: int, channel_id: int):
        """Updates jail channel for the guild."""
        if await self.get_guild_configuration(guild_id) is None:
            await self.create_new_guild_configuration(guild_id, jail_id=channel_id)
            return
        await self.db["Guild_configurations"].update_one(
            {'guild_id': guild_id},
            {'$set': {'jail_channel': bson.Int64(channel_id)}}
        )

    async def update_guild_jail_role(self, guild_id: int, role_id: int):
        """Updates jail role for the guild."""
        if await self.get_guild_configuration(guild_id) is None:
            await self.create_new_guild_configuration(guild_id, jail_role_id=role_id)
            return
        await self.db["Guild_configurations"].update_one(
            {'guild_id': guild_id},
            {'$set': {'jail_role': bson.Int64(role_id)}}
        )

    async def update_guild_mute_role(self, guild_id: int, role_id: int):
        """Updates mute role for the guild."""
        if await self.get_guild_configuration(guild_id) is None:
            await self.create_new_guild_configuration(guild_id, mute_role_id=role_id)
            return
        await self.db["Guild_configurations"].update_one(
            {'guild_id': guild_id},
            {'$set': {'mute_role': bson.Int64(role_id)}}
        )

    """FAQ related methods"""

    async def get_faq_entry(self, term: str) -> Union[list, None]:
        """Returns a dictionary list of frequently asked questions based on the query."""
        cursor = self.db["FAQ"].find(
            {"$or": [
                {"question": {"$regex": term, "$options": "i"}},
                {"tags": term}
            ]}
        ).sort("question", 1)
        return [i async for i in cursor] or None

    async def get_faq_entries(self) -> list:
        """Returns a dictionary list of all frequently asked questions."""
        cursor = self.db["FAQ"].find({}).sort("question", 1)
        return [i async for i in cursor]

    """Shitpost related methods"""

    async def get_random_shitpost(self, last_posts: List[Union[ObjectId, int]]) -> dict:
        """Returns a random shitpost."""
        data = await self.db["Shitposts"].find_one(
            {"_id": {"$nin": last_posts}}
        ).sort("times_shown", 1)
        cursor = self.db["Punishments"].find({
            "_id": {"$nin": last_posts}, "times_shown": data["times_shown"]
        })
        return random.choice([i async for i in cursor])

    async def log_shitpost(self, object_id: ObjectId) -> None:
        """Marks shitpost by specified ID as read by increasing times_shown."""
        await self.db["Shitposts"].update_one(
            {'_id': object_id},
            {'$inc': {'times_shown': 1}}
        )


def setup(client):
    pass

def teardown(client):
    pass