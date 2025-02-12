import discord # type: ignore

from discord.ext import commands
from discord.ext.commands.context import Context # type: ignore
from typing import Optional, Union

from pidroid.client import Pidroid
from pidroid.cogs.models.case import CasePaginator
from pidroid.cogs.models.categories import ModerationCategory
from pidroid.cogs.utils.checks import check_junior_moderator_permissions, check_normal_moderator_permissions
from pidroid.cogs.utils.decorators import command_checks
from pidroid.cogs.utils.embeds import PidroidEmbed, ErrorEmbed
from pidroid.cogs.utils.paginators import PidroidPages


class ModeratorInfoCommands(commands.Cog): # type: ignore
    """This class implements cog which contains commands for viewing and editing moderation logs and statistics."""

    def __init__(self, client: Pidroid):
        self.client = client

    @commands.command( # type: ignore
        brief='Displays details for the specified case.\nCases can be modified by providing a reason parameter.',
        usage='<case ID> [reason]',
        category=ModerationCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @command_checks.is_junior_moderator(kick_members=True) # type: ignore
    @commands.guild_only() # type: ignore
    async def case(self, ctx: Context, case_id: int, *, reason: Optional[str]):
        assert ctx.guild is not None
        case = await self.client.fetch_case(ctx.guild.id, case_id)

        if reason is not None:
            check_normal_moderator_permissions(ctx, kick_members=True)
            await case.update_reason(reason)
            return await ctx.reply("Case details updated successfully!")

        await ctx.reply(embed=case.to_embed())

    @commands.command( # type: ignore
        name='invalidate-warning',
        brief='Invalidates specified warning.',
        usage='<case ID>',
        aliases=['invalidate-warn', 'invalidatewarn', 'invalidatewarning'],
        category=ModerationCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @command_checks.is_senior_moderator(manage_guild=True)
    @commands.guild_only() # type: ignore
    async def invalidatewarning(self, ctx: Context, case_id: int):
        assert ctx.guild is not None
        case = await self.client.fetch_case(ctx.guild.id, case_id)
        await case.invalidate()
        await ctx.reply('Warning invalidated successfully!')

    @commands.command( # type: ignore
        brief='Displays all active warnings for the specified user.',
        usage='[user] [all]',
        aliases=['warns'],
        category=ModerationCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @commands.guild_only() # type: ignore
    async def warnings(self, ctx: Context, user: Union[discord.Member, discord.User] = None, amount: str = 'none'):
        assert ctx.guild is not None
        user = user or ctx.author

        error_msg = "I could not find any warnings for you!"
        if user.id != ctx.author.id:
            check_junior_moderator_permissions(ctx, kick_members=True)
            error_msg = "Specified user has no warnings."

        if amount.lower() == 'all':
            warnings = await self.client.fetch_warnings(ctx.guild.id, user.id)
        else:
            warnings = await self.client.fetch_active_warnings(ctx.guild.id, user.id)

        if len(warnings) == 0:
            return await ctx.reply(embed=ErrorEmbed(error_msg))

        pages = PidroidPages(
            source=CasePaginator(f"Displaying warnings for {str(user)}", warnings, True),
            ctx=ctx
        )
        await pages.start()

    @commands.command( # type: ignore
        brief='Displays all moderation logs for the specified user.',
        usage='[user]',
        category=ModerationCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @commands.guild_only() # type: ignore
    async def modlogs(self, ctx: Context, user: Union[discord.Member, discord.User] = None):
        assert ctx.guild is not None
        user = user or ctx.author

        error_msg = "I could not find any modlogs related to you!"
        if user.id != ctx.author.id:
            check_junior_moderator_permissions(ctx, kick_members=True)
            error_msg = "Specified user has no modlogs!"

        cases = await self.client.fetch_cases(ctx.guild.id, user.id)

        if len(cases) == 0:
            return await ctx.reply(embed=ErrorEmbed(error_msg))

        pages = PidroidPages(
            source=CasePaginator(f"Displaying moderation logs for {str(user)}", cases),
            ctx=ctx
        )
        await pages.start()

    @commands.command( # type: ignore
        brief='Displays moderation statistics for the specified member.',
        usage='[member]',
        category=ModerationCategory
    )
    @commands.bot_has_permissions(send_messages=True) # type: ignore
    @command_checks.is_junior_moderator(kick_members=True)
    @commands.guild_only() # type: ignore
    async def modstats(self, ctx: Context, member: discord.Member = None):
        assert ctx.guild is not None
        member = member or ctx.author
        data = await self.client.api.fetch_moderation_statistics(ctx.guild.id, member.id)
        embed = PidroidEmbed(title=f'Displaying moderation statistics for {str(member)}')
        embed.add_field(name='Bans', value=data["bans"])
        embed.add_field(name='Kicks', value=data["kicks"])
        embed.add_field(name='Jails', value=data["jails"])
        embed.add_field(name='Warnings', value=data["warnings"])
        embed.add_field(name='Moderator total', value=data["user_total"])
        embed.add_field(name='Server total', value=data["guild_total"])
        await ctx.reply(embed=embed)


async def setup(client: Pidroid):
    await client.add_cog(ModeratorInfoCommands(client))
