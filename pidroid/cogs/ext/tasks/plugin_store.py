from aiohttp.client_exceptions import ServerDisconnectedError
from datetime import timedelta
from discord.channel import TextChannel
from discord.ext import tasks, commands # type: ignore
from typing import List

from pidroid.client import Pidroid
from pidroid.cogs.utils.checks import is_client_pidroid
from pidroid.cogs.utils.parsers import truncate_string
from pidroid.cogs.utils.time import timedelta_to_datetime

class PluginStoreTasks(commands.Cog): # type: ignore
    """This class implements a cog for handling of automatic tasks related to TheoTown's plugin store."""

    def __init__(self, client: Pidroid) -> None:
        self.client = client

        self.use_threads = True
        self.add_reactions = True

        self.new_plugins_cache: List[int] = []

        self.retrieve_new_plugins.start()

    def cog_unload(self):
        """Ensure that tasks are cancelled on cog unload."""
        self.retrieve_new_plugins.cancel()

    @tasks.loop(seconds=30)
    async def retrieve_new_plugins(self) -> None:
        """Retrieves new plugin store plugins and publishes them to TheoTown guild channel."""
        
        await self.client.fetch_channel(640522649033769000)
        
        channel = await self.client.get_or_fetch_channel(640522649033769000)
        if channel is None:
            return self.client.logger.warning("Showcase channel returned a None!")
        assert isinstance(channel, TextChannel)

        try:
            last_approval_time = self.client.persistent_data.data.get("last plugin approval", -1)

            plugins = await self.client.api.fetch_new_plugins(last_approval_time)

            if len(plugins) == 0:
                self.new_plugins_cache = []
                return

            latest_approval_time = plugins[0].time

            if latest_approval_time > last_approval_time:

                self.client.persistent_data.data.update({"last plugin approval": latest_approval_time})
                self.client.persistent_data.save()

                for plugin in plugins:

                    if plugin.id in self.new_plugins_cache:
                        continue
                    self.new_plugins_cache.append(plugin.id)

                    message = await channel.send(embed=plugin.to_embed())

                    if self.add_reactions:
                        await message.add_reaction("👍")
                        await message.add_reaction("👎")

                    if self.use_threads:
                        await self.client.create_expiring_thread(
                            message, f"{truncate_string(plugin.clean_title, 89)} discussion",
                            timedelta_to_datetime(timedelta(days=7))
                        )
        except ServerDisconnectedError:
            self.client.logger.exception("An server disconnection was encountered while trying to retrieve and publish new plugin information")
        except Exception:
            self.client.logger.exception("An exception was encountered while trying to retrieve and publish new plugin information")

    @retrieve_new_plugins.before_loop
    async def before_new_plugin_retriever(self) -> None:
        """Runs before retrieve_new_plugins task to ensure that the task is allowed to run."""
        await self.client.wait_until_ready()
        if not is_client_pidroid(self.client):
            self.retrieve_new_plugins.cancel()

async def setup(client: Pidroid) -> None:
    await client.add_cog(PluginStoreTasks(client))
