from discord import Game
from discord.ext import commands

from client import Pidroid

class InvocationEventHandler(commands.Cog):
    """This class implements a cog for handling invocation of functions upon internal bot cache being prepared."""

    def __init__(self, client: Pidroid) -> None:
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """This notifies the host of the bot that the client is ready to use."""
        print(f'{self.client.user.name} bot (build {self.client.full_version}) has started with the ID of {self.client.user.id}')
        await self.client.change_presence(activity=Game("TheoTown"))


def setup(client: Pidroid) -> None:
    client.add_cog(InvocationEventHandler(client))
