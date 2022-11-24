import datetime
import os
import random

from contextlib import suppress
from datetime import timedelta
from discord.ext import commands # type: ignore
from discord.errors import HTTPException, Forbidden
from discord.ext.commands import BadArgument # type: ignore
from discord.ext.commands.context import Context # type: ignore
from discord.member import Member
from discord.message import Message
from typing import Optional

from pidroid.client import Pidroid
from pidroid.cogs.models.categories import TheoTownCategory
from pidroid.cogs.models.exceptions import InvalidChannel
from pidroid.cogs.utils import http
from pidroid.cogs.utils.checks import is_guild_theotown, is_channel_bot_commands
from pidroid.cogs.utils.decorators import command_checks
from pidroid.cogs.utils.embeds import PidroidEmbed, ErrorEmbed, SuccessEmbed
from pidroid.cogs.utils.http import Route
from pidroid.cogs.utils.paginators import PidroidPages, PluginListPaginator
from pidroid.cogs.utils.parsers import format_version_code, truncate_string
from pidroid.cogs.utils.time import timedelta_to_datetime
from pidroid.cogs.utils.time import utcnow
from pidroid.constants import THEOTOWN_GUILD, BOT_COMMANDS_CHANNEL

SUPPORTED_GALLERY_MODES = ['recent', 'trends', 'rating']

def handle_wrong_gallery_modes(query: str) -> Optional[str]:
    if query in ["trending", "hot", "trends"]:
        return "trends"
    if query in ["new", "recent", "latest"]:
        return "recent"
    if query in ["rating", "top", "best"]:
        return "rating"
    return None

class TheoTownCommands(commands.Cog): # type: ignore
    """This class implements a cog for TheoTown API related commands."""

    def __init__(self, client: Pidroid) -> None:
        self.client = client
        self.api = self.client.api

    @commands.command( # type: ignore
        brief="Returns the latest game version of TheoTown for all platforms.",
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user) # type: ignore
    async def version(self, ctx: Context):
        async with ctx.typing():
            cache = self.client.version_cache
            embed = PidroidEmbed(title="Most recent versions of TheoTown")
            async with await http.get(self.client, "https://bd.theotown.com/get_version") as response:
                version_data = await response.json()
            for version_name in version_data:
                # Ignore Amazon since it's not updated
                if version_name == 'Amazon':
                    continue

                version = format_version_code(version_data[version_name]['version'])
                url: Optional[str] = None
                if version not in cache or cache[version] is None:
                    self.client.logger.info(f'URL for version {version} not found in internal cache, querying the API')

                    res = await self.api.get(Route("/private/game/lookup_version", {"query": version}))

                    if res["success"]:
                        url = res["data"]["url"]
                        self.client.logger.info(f'Version URL found, internal cache updated with {url}')

                    cache[version] = url
                url = cache[version]
                value = f'[{version}]({url})'
                if url is None:
                    value = version
                embed.add_field(name=version_name, value=value)
            self.client.version_cache = cache
            embed.set_footer(text='Note: this will also include versions which are not yet available to regular users.')
            await ctx.reply(embed=embed)

    @commands.command( # type: ignore
        brief="Returns TheoTown's online mode statistics.",
        aliases=["multiplayer"],
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @commands.guild_only() # type: ignore
    @commands.cooldown(rate=1, per=15, type=commands.BucketType.channel) # type: ignore
    @commands.max_concurrency(number=3, per=commands.BucketType.guild) # type: ignore
    async def online(self, ctx: Context):
        async with ctx.typing():
            res = await self.api.get(Route("/private/game/get_online_statistics"))

            data = res["data"]
            total_plots = data["plots"]["total"]
            free_plots = data["plots"]["free"]
            region_count = data["region_count"]
            population = data["population"]

            # Build and send the embed
            embed = PidroidEmbed(title='Online mode statistics')
            embed.add_field(name='Active regions', value=f'{region_count:,}')
            embed.add_field(name='Total plots', value=f'{total_plots:,}')
            embed.add_field(name='Free plots', value=f'{free_plots:,}')
            embed.add_field(name='Total population', value=f'{population:,}')
            await ctx.reply(embed=embed)

    @commands.command( # type: ignore
        brief='Returns an image from TheoTown\'s in-game gallery.',
        usage='[recent/trends/rating] [random number]',
        aliases=['screenshot'],
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user) # type: ignore
    async def gallery(self, ctx: Context, mode: str = 'recent', number: int = None):
        async with ctx.typing():
            selected_mode = handle_wrong_gallery_modes(mode.lower())

            if selected_mode not in SUPPORTED_GALLERY_MODES:
                self.gallery.reset_cooldown(ctx)
                return await ctx.reply(embed=ErrorEmbed(
                    'Wrong mode specified. Allowed modes are `' + '`, `'.join(SUPPORTED_GALLERY_MODES) + '`.'
                ))

            if number is None:
                number = random.randint(1, 200) # nosec

            try:
                number = int(number)
            except Exception:
                self.gallery.reset_cooldown(ctx)
                return await ctx.reply(embed=ErrorEmbed('Your specified position is incorrect.'))

            if number not in range(1, 201):
                self.gallery.reset_cooldown(ctx)
                return await ctx.reply(embed=ErrorEmbed('Number must be between 1 and 200!'))

            res = await self.client.api.get(Route("/public/game/gallery", {"mode": selected_mode, "limit": number}))
            if not res["success"]:
                return await ctx.reply(embed=ErrorEmbed("Unable to retrieve gallery data!"))

            data = res["data"]
            screenshot = data[number - 1]

            embed = PidroidEmbed(title=screenshot['name'])
            embed.set_image(url=screenshot['image'])
            embed.set_footer(text=f'#{screenshot["id"]}')
            await ctx.reply(embed=embed)

    @commands.command( # type: ignore
        name='find-plugin',
        brief='Searches plugin store for the specified plugin.',
        usage='<query>',
        aliases=['findplugin'],
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @commands.guild_only() # type: ignore
    @commands.cooldown(rate=2, per=10, type=commands.BucketType.user) # type: ignore
    async def findplugin(self, ctx: Context, *, query: Optional[str]): # noqa
        async with ctx.typing():
            if query is None:
                await ctx.reply(embed=ErrorEmbed('I could not find a query to find a plugin.'))
                self.findplugin.reset_cooldown(ctx)
                return

            is_id = query.startswith("#")
            if is_id:
                try:
                    pl_id = int(query.replace("#", ""))
                except ValueError:
                    await ctx.reply(embed=ErrorEmbed('You specified an invalid plugin ID!'))
                    self.findplugin.reset_cooldown(ctx)
                    return

            if not is_id and len(query) <= 2:
                await ctx.reply(embed=ErrorEmbed('Your query is too short! Please keep it at least 3 characters long.'))
                self.findplugin.reset_cooldown(ctx)
                return

            if not is_id and len(query) > 30:
                await ctx.reply(embed=ErrorEmbed('Your query is too long, please keep it below 30 characters!'))
                self.findplugin.reset_cooldown(ctx)
                return

            async with ctx.channel.typing():
                if is_id:
                    assert pl_id is not None
                    plugin_list = await self.api.fetch_plugin_by_id(pl_id)
                else:
                    plugin_list = await self.api.search_plugins(query)

            plugin_count = len(plugin_list)
            if plugin_count == 0:
                return await ctx.reply(embed=ErrorEmbed('No plugin could be found by your query.'))

            index = 0
            if plugin_count > 1:
                found = False
                for i, plugin in enumerate(plugin_list):
                    if str(plugin.id) == query.replace("#", ""):
                        index = i
                        found = True
                        break

                if not found:
                    pages = PidroidPages(PluginListPaginator(plugin_list), ctx=ctx)
                    return await pages.start()

            await ctx.reply(embed=plugin_list[index].to_embed())

    @commands.command( # type: ignore
        name='download-plugin',
        brief='Downloads a plugin by the specified ID.',
        usage='<plugin ID>',
        permissions=["TheoTown developer"],
        aliases=['downloadplugin'],
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @command_checks.is_theotown_developer()
    async def downloadplugin(self, ctx: Context, *, plugin_id: int = None):
        async with ctx.typing():
            if plugin_id is None:
                await ctx.reply(embed=ErrorEmbed('I could not find an ID of the plugin to download!'))
                self.downloadplugin.reset_cooldown(ctx)
                return

            plugins = await self.api.fetch_plugin_by_id(plugin_id, True)
            if len(plugins) == 0:
                return await ctx.reply(embed=ErrorEmbed("I could not find any plugins to download by the specified ID!"))

            plugin = plugins[0]
            if plugin.download_url is None:
                return await ctx.reply(embed=ErrorEmbed(
                    f"Failure encountered while trying to retrieve the plugin file for '{plugin.clean_title}'!"
                ))

            await ctx.author.send(f"Here's a link for '{plugin.clean_title}' plugin: {plugin.download_url}")
            await ctx.reply(f"The download link for '{plugin.clean_title}' plugin has been sent to you via a DM!")

    @commands.command( # type: ignore
        brief='Send a feature suggestion to the suggestions channel.',
        usage='<suggestion>',
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True, attach_files=True, add_reactions=True) # type: ignore # permissions kind of obsolete
    @commands.cooldown(rate=1, per=60 * 5, type=commands.BucketType.user) # type: ignore
    @command_checks.guild_configuration_exists()
    async def suggest(self, ctx: Context, *, suggestion: str = None): # noqa C901
        is_theotown = is_guild_theotown(ctx.guild)
        if is_theotown:
            if not is_channel_bot_commands(ctx.channel):
                raise InvalidChannel(f'The command can only be used inside <#{BOT_COMMANDS_CHANNEL}> channel')

        if not self.client.guild_config_cache_ready:
            return
        guild_config = self.client.get_guild_configuration(ctx.guild.id)
        if guild_config.suggestion_channel is None:
            return await ctx.reply(embed=ErrorEmbed("Suggestion channel has not been setup."))

        if suggestion is None:
            await ctx.reply(embed=ErrorEmbed('Your suggestion cannot be empty!'))
            self.suggest.reset_cooldown(ctx)
            return

        if len(suggestion) < 4:
            await ctx.reply(embed=ErrorEmbed('Your suggestion is too short!'))
            self.suggest.reset_cooldown(ctx)
            return

        # If suggestion text is above discord embed description limit
        if len(suggestion) > 2048:
            await ctx.reply(embed=ErrorEmbed('The suggestion is too long!'))
            self.suggest.reset_cooldown(ctx)
            return

        attachment_url = None
        file = None
        channel = self.client.get_channel(guild_config.suggestion_channel)

        if channel is None:
            return await ctx.reply(embed=ErrorEmbed("Suggestion channel not found!"))

        embed = PidroidEmbed(description=suggestion)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        attachments = ctx.message.attachments
        if attachments:

            if len(attachments) > 1:
                await ctx.reply(embed=ErrorEmbed('Only one picture can be submitted for a suggestion!'))
                self.suggest.reset_cooldown(ctx)
                return

            attachment = attachments[0]
            if attachment.size >= 7000000:
                await ctx.reply(embed=ErrorEmbed('Your image is too big to be uploaded!'))
                self.suggest.reset_cooldown(ctx)
                return

            filename = attachment.filename
            extension = os.path.splitext(filename)[1]
            if extension.lower() not in ['.png', '.jpg', '.jpeg']:
                await ctx.reply(embed=ErrorEmbed('Could not submit a suggestion: unsupported file extension. Only image files are supported!'))
                self.suggest.reset_cooldown(ctx)
                return

            file = await attachment.to_file()
            embed.set_image(url=f'attachment://{filename}')

        async with ctx.typing():
            message: Message = await channel.send(embed=embed, file=file)
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            if is_theotown:
                await message.add_reaction("❗")
                await message.add_reaction("❕")
                await message.add_reaction("⛔")

            if message.embeds[0].image.url is not None:
                attachment_url = message.embeds[0].image.url
            if is_theotown:
                s_id = await self.api.submit_suggestion(ctx.author.id, message.id, suggestion, attachment_url)
                embed.set_footer(text=f'✅ I like this idea; ❌ I hate this idea; ❗ Already possible ❕ Already possible with plugin(s).\n#{s_id}')
            else:
                embed.set_footer(text='✅ I like this idea; ❌ I hate this idea.')
            await message.edit(embed=embed)
            if guild_config.use_suggestion_threads:
                await self.client.create_expiring_thread(message, f"{truncate_string(suggestion, 89)} discussion", timedelta_to_datetime(timedelta(days=7)))
            with suppress(HTTPException):
                await ctx.reply(f'Your suggestion has been submitted to <#{guild_config.suggestion_channel}> channel successfully!')

    @commands.command( # type: ignore
        name='link-account',
        brief='Links a discord user account to a TheoTown account.',
        usage='<member> <forum user ID>',
        category=TheoTownCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @command_checks.is_theotown_developer()
    async def link_account(self, ctx: Context, member: Member, forum_id: int):
        # Check if the discord account is linked to anything
        linked_acc = await self.client.api.fetch_linked_account_by_user_id(member.id)
        if linked_acc:
            raise BadArgument(f"{str(member)} is already linked to a forum account!")

        # Check if the forum account is linked to anything
        linked_acc = await self.client.api.fetch_linked_account_by_forum_id(forum_id)
        if linked_acc:
            raise BadArgument("Specified forum account is already linked to a discord account!")

        account = await self.client.api.fetch_theotown_account_by_id(forum_id)
        if account is None:
            raise BadArgument("Specified game account does not exist!")

        await self.client.api.insert_linked_account(member.id, forum_id)
        await ctx.send(embed=SuccessEmbed(
            f"Discord account {member.mention} has been linked to [{account.forum_account.name}]({account.forum_account.profile_url}) successfully!"
        ))

    @commands.command( # type: ignore
        name='redeem-wage',
        brief='Redeems moderation wage for the linked TheoTown account.',
        category=TheoTownCategory
    )
    @commands.max_concurrency(number=1, per=commands.BucketType.user) # type: ignore
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    async def redeem_wage(self, ctx: Context):
        # Find the linked account
        linked_acc = await self.client.api.fetch_linked_account_by_user_id(ctx.author.id)
        if linked_acc is None:
            raise BadArgument(f"Your discord account is not linked to any TheoTown accounts!")

        # Check if last redeem was not within this month
        last_wage_date: datetime.datetime = linked_acc.date_wage_last_redeemed
        if last_wage_date is not None and last_wage_date.month == utcnow().month:
            raise BadArgument("You've already redeemed the wage for this month!")
        
        # Obtain TT guild
        try:
            guild = await self.client.fetch_guild(THEOTOWN_GUILD, with_counts=False)
        except Forbidden:
            raise BadArgument("Pidroid cannot find the TheoTown server, I cannot determine your wage!")

        # Obtain the member
        member = await self.client.get_or_fetch_member(guild, ctx.author.id)
        if member is None:
            raise BadArgument("You are not a member of the TheoTown server, I cannot determine your wage!")

        # Determine reward by role ID
        roles = [r.id for r in member.roles if r.id in [
            410512375083565066, 368799288127520769, 381899421992091669,
            710914534394560544, 365482773206532096
        ]]

        if len(roles) == 0:
            raise BadArgument("You are not eligible for a wage!")

        # Actual transaction
        res = await self.client.api.get(Route(
            "/private/game/redeem_wage",
            {"forum_id": linked_acc.forum_id, "role_id": roles[-1]}
        ))
        if res["success"]:
            data = res["data"]
            await self.client.api.update_linked_account_by_user_id(member.id, utcnow())
            return await ctx.reply(f'{data["diamonds_paid"]:,} diamonds have been redeemed to the {data["user"]["name"]} account!')
        raise BadArgument(res["details"])

async def setup(client: Pidroid) -> None:
    await client.add_cog(TheoTownCommands(client))
