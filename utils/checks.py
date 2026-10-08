"""Permission checks."""
import discord
from discord import app_commands

from utils.config import load_config


class NotAdmin(app_commands.CheckFailure):
    """Raised by the admin_only() check; the tree error handler reports it to the user."""


def is_admin(user: discord.abc.User) -> bool:
    """
    Check if a user is a bot admin.

    Server administrators always count, so a fresh install can be configured
    before anyone is listed in admin_ids. Otherwise the user must be listed in
    admin_ids or hold one of the admin_role_ids roles.
    """
    # Outside a guild there are no roles or permissions to check
    if not isinstance(user, discord.Member):
        return False

    if user.guild_permissions.administrator:
        return True

    config = load_config()
    admin_ids = config.get("admin_ids") or []
    admin_role_ids = config.get("admin_role_ids") or []

    if user.id in admin_ids:
        return True

    return any(role.id in admin_role_ids for role in user.roles)


def admin_only():
    """App-command check that only lets bot admins run the command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            raise NotAdmin("❌ Only admins can use this command.")
        return True

    return app_commands.check(predicate)
