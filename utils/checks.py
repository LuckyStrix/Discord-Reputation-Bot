"""Permission checks."""
import discord

from utils.config import load_config


def is_admin(user: discord.Member) -> bool:
    """Check if a user is an admin (either by user ID or role ID)"""
    config = load_config()
    admin_ids = config.get("admin_ids", [])
    admin_role_ids = config.get("admin_role_ids", [])
    
    # Check user ID
    if user.id in admin_ids:
        return True
    
    # Check role IDs
    user_role_ids = [role.id for role in user.roles]
    if any(role_id in admin_role_ids for role_id in user_role_ids):
        return True
    
    return False
