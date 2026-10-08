"""Admin cog: configuration and admin-management slash commands."""
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only, is_admin
from utils.config import load_config, save_config
from views.settings import SettingsView


class Admin(commands.Cog):
    """Configuration and admin-management slash commands."""

    @app_commands.command(name="channel_set", description="Add a forum channel for tracking reps (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(channel="Forum channel to activate rep tracking on.")
    async def channel_set(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        config = load_config()
        config.setdefault("forums", [])
        if channel.id not in config["forums"]:
            config["forums"].append(channel.id)
            save_config(config)
            await interaction.response.send_message(
                f"✅ Channel {channel.mention} added to rep tracking.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "This channel is already tracked.", ephemeral=True
            )

    @app_commands.command(name="log", description="Set a channel for review logs (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(channel="The channel to send review logs to.")
    async def log_set(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_config()
        config["log_channel"] = channel.id
        save_config(config)
        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"Review logs will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_add", description="Add a user as admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(user="The user to add as admin.")
    async def admin_add(self, interaction: discord.Interaction, user: discord.Member):
        config = load_config()
        admin_ids = config.get("admin_ids", [])
        
        # Check if target is already admin
        if is_admin(user):
            await interaction.response.send_message(
                f"{user.mention} is already an admin.", ephemeral=True
            )
            return
            
        # Add the new admin (add to user IDs by default)
        admin_ids.append(user.id)
        config["admin_ids"] = admin_ids
        
        save_config(config)
            
        embed = discord.Embed(
            title="✅ Admin Added",
            description=f"{user.mention} has been added as an admin.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_remove", description="Remove a user from admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(user="The user to remove from admin.")
    async def admin_remove(self, interaction: discord.Interaction, user: discord.Member):
        config = load_config()
        admin_ids = config.get("admin_ids", [])
        
        # Check if target is admin by user ID (only remove from user IDs, not roles)
        if user.id not in admin_ids:
            await interaction.response.send_message(
                f"{user.mention} is not an admin.", ephemeral=True
            )
            return
            
        # Don't allow self-removal if only admin
        if user.id == interaction.user.id and len(admin_ids) == 1:
            await interaction.response.send_message(
                "❌ Cannot remove yourself as the last admin.", ephemeral=True
            )
            return
            
        # Remove the admin
        admin_ids.remove(user.id)
        config["admin_ids"] = admin_ids
        
        save_config(config)
            
        embed = discord.Embed(
            title="✅ Admin Removed",
            description=f"{user.mention} has been removed from admin.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_list", description="List all admins (admin only).")
    @app_commands.guild_only()
    @admin_only()
    async def admin_list(self, interaction: discord.Interaction):
        config = load_config()
        admin_ids = config.get("admin_ids", [])
        admin_role_ids = config.get("admin_role_ids", [])
        
        embed = discord.Embed(
            title="👑 Admin List",
            description="Current bot administrators:",
            color=discord.Color.purple()
        )
        
        if not admin_ids and not admin_role_ids:
            embed.description = "No admins configured."
        else:
            # Show admin users
            if admin_ids:
                admin_mentions = []
                for admin_id in admin_ids:
                    member = interaction.guild.get_member(admin_id)
                    if member:
                        admin_mentions.append(f"• {member.mention} ({member.display_name})")
                    else:
                        admin_mentions.append(f"• <@{admin_id}> (ID: {admin_id})")
                
                embed.add_field(
                    name=f"Admin Users ({len(admin_ids)})",
                    value="\n".join(admin_mentions),
                    inline=False
                )
            
            # Show admin roles
            if admin_role_ids:
                role_mentions = []
                for role_id in admin_role_ids:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        role_mentions.append(f"• {role.mention} ({role.name})")
                    else:
                        role_mentions.append(f"• <@&{role_id}> (ID: {role_id})")
                
                embed.add_field(
                    name=f"Admin Roles ({len(admin_role_ids)})",
                    value="\n".join(role_mentions),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_role_add", description="Add a role as admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(role="The role to add as admin.")
    async def admin_role_add(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config()
        admin_role_ids = config.get("admin_role_ids", [])
        
        # Check if role is already admin
        if role.id in admin_role_ids:
            await interaction.response.send_message(
                f"{role.mention} is already an admin role.", ephemeral=True
            )
            return
            
        # Add the new admin role
        admin_role_ids.append(role.id)
        config["admin_role_ids"] = admin_role_ids
        
        save_config(config)
            
        embed = discord.Embed(
            title="✅ Admin Role Added",
            description=f"{role.mention} has been added as an admin role.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_role_remove", description="Remove a role from admin (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(role="The role to remove from admin.")
    async def admin_role_remove(self, interaction: discord.Interaction, role: discord.Role):
        config = load_config()
        admin_role_ids = config.get("admin_role_ids", [])
        
        # Check if role is admin
        if role.id not in admin_role_ids:
            await interaction.response.send_message(
                f"{role.mention} is not an admin role.", ephemeral=True
            )
            return
            
        # Remove the admin role
        admin_role_ids.remove(role.id)
        config["admin_role_ids"] = admin_role_ids
        
        save_config(config)
            
        embed = discord.Embed(
            title="✅ Admin Role Removed",
            description=f"{role.mention} has been removed from admin roles.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="auto_close_toggle", description="Toggle the auto-close feature on/off (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(enabled="Enable or disable auto-close feature")
    async def auto_close_toggle(self, interaction: discord.Interaction, enabled: bool = None):
        config = load_config()
        
        # If no parameter provided, show current status
        if enabled is None:
            current_status = config.get("auto_close_enabled", True)
            current_hours = config.get("auto_close_hours", 24)
            
            embed = discord.Embed(
                title="⚙️ Auto-Close Settings",
                description=f"**Status:** {'✅ Enabled' if current_status else '❌ Disabled'}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Auto-Close Timer", value=f"{current_hours} hours", inline=True)
            embed.add_field(name="Usage", value="Use `/auto_close_toggle true/false` to change", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update the setting
        old_status = config.get("auto_close_enabled", True)
        config["auto_close_enabled"] = enabled
        
        save_config(config)
        
        # Create response embed
        status_text = "✅ Enabled" if enabled else "❌ Disabled"
        color = discord.Color.green() if enabled else discord.Color.red()
        
        embed = discord.Embed(
            title="⚙️ Auto-Close Setting Updated",
            description=f"Auto-close feature is now **{status_text}**",
            color=color
        )
        
        if enabled:
            hours = config.get("auto_close_hours", 24)
            embed.add_field(
                name="Timer", 
                value=f"Threads will auto-close {hours} hours after first review", 
                inline=False
            )
        else:
            embed.add_field(
                name="Note", 
                value="Existing scheduled auto-closes will still occur unless manually cancelled", 
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the change to log channel
        config_log = load_config()
        log_ch_id = config_log.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🔧 Auto-Close Setting Changed",
                    description=f"{interaction.user.mention} **{'enabled' if enabled else 'disabled'}** the auto-close feature",
                    color=color
                )
                log_embed.add_field(name="Previous Status", value="✅ Enabled" if old_status else "❌ Disabled", inline=True)
                log_embed.add_field(name="New Status", value=status_text, inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
        
        print(f"[AUTO-CLOSE] {interaction.user} ({'enabled' if enabled else 'disabled'}) auto-close feature")

    @app_commands.command(name="auto_close_hours", description="Set the number of hours before auto-close (admin only).")
    @app_commands.guild_only()
    @admin_only()
    @app_commands.describe(hours="Number of hours to wait before auto-closing threads (1-168)")
    async def auto_close_hours(self, interaction: discord.Interaction, hours: int):
        # Validate hours (1 hour to 1 week)
        if not (1 <= hours <= 168):
            await interaction.response.send_message(
                "❌ Hours must be between 1 and 168 (1 week).", ephemeral=True
            )
            return
        
        config = load_config()
        old_hours = config.get("auto_close_hours", 24)
        config["auto_close_hours"] = hours
        
        save_config(config)
        
        embed = discord.Embed(
            title="⏰ Auto-Close Timer Updated",
            description=f"Auto-close timer set to **{hours} hours**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Previous", value=f"{old_hours} hours", inline=True)
        embed.add_field(name="New", value=f"{hours} hours", inline=True)
        embed.add_field(
            name="Note", 
            value="This only affects new auto-close schedules. Existing ones keep their original timing.", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Log the change
        config_log = load_config()
        log_ch_id = config_log.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="⏰ Auto-Close Timer Changed",
                    description=f"{interaction.user.mention} changed auto-close timer from **{old_hours}h** to **{hours}h**",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
        
        print(f"[AUTO-CLOSE] {interaction.user} changed auto-close timer to {hours} hours")

    @app_commands.command(name="settings", description="View and modify bot settings through an interactive interface (admin only).")
    @app_commands.guild_only()
    @admin_only()
    async def settings_command(self, interaction: discord.Interaction):
        # Create the settings view and embed
        view = SettingsView(interaction)
        embed = await view.create_main_settings_embed(interaction)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Log settings access
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="⚙️ Settings Panel Accessed",
                    description=f"{interaction.user.mention} opened the settings dashboard",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)

        print(f"[SETTINGS] {interaction.user} accessed settings dashboard")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
