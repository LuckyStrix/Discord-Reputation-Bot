"""Interactive /settings panel and the modals behind each button."""
from datetime import datetime

import discord

from utils.checks import is_admin
from utils.config import load_config, save_config
from utils.presence import apply_bot_status


class SettingsView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)  # 5 minute timeout
        self.interaction = interaction

    @discord.ui.button(label="🔧 Auto-Close Settings", style=discord.ButtonStyle.primary, row=0)
    async def auto_close_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can modify settings.", ephemeral=True)
        
        modal = AutoCloseSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 TOS Settings", style=discord.ButtonStyle.secondary, row=0)
    async def tos_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can modify settings.", ephemeral=True)
        
        modal = TOSSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👑 Admin Settings", style=discord.ButtonStyle.success, row=1)
    async def admin_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can view admin settings.", ephemeral=True)
        
        embed = await self.create_admin_settings_embed(interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🤖 Bot Status", style=discord.ButtonStyle.secondary, row=1)
    async def bot_status_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("❌ Only admins can modify settings.", ephemeral=True)
        
        modal = BotStatusSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.gray, row=2)
    async def refresh_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.create_main_settings_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_main_settings_embed(self, interaction: discord.Interaction):
        config = load_config()
        
        embed = discord.Embed(
            title="⚙️ Bot Settings Dashboard",
            description="Click the buttons below to view or modify specific settings",
            color=discord.Color.blue()
        )

        # Auto-Close Settings
        auto_close_enabled = config.get("auto_close_enabled", True)
        auto_close_hours = config.get("auto_close_hours", 24)
        admin_confirmation = config.get("admin_close_confirmation", True)
        embed.add_field(
            name="🔧 Auto-Close Settings",
            value=f"**Status:** {'✅ Enabled' if auto_close_enabled else '❌ Disabled'}\n**Timer:** {auto_close_hours} hours\n**Admin Confirm:** {'✅ Yes' if admin_confirmation else '❌ No'}",
            inline=True
        )

        # Forum Settings
        forums = config.get("forums", [])
        forum_count = len(forums)
        embed.add_field(
            name="📁 Forum Channels",
            value=f"**Tracking:** {forum_count} forum{'s' if forum_count != 1 else ''}",
            inline=True
        )

        # Log Channel
        log_channel = config.get("log_channel")
        log_status = f"<#{log_channel}>" if log_channel else "Not set"
        embed.add_field(
            name="📝 Log Channel",
            value=f"**Channel:** {log_status}",
            inline=True
        )

        # Admin Settings
        admin_ids = len(config.get("admin_ids", []))
        admin_roles = len(config.get("admin_role_ids", []))
        embed.add_field(
            name="👑 Admin Settings",
            value=f"**Users:** {admin_ids}\n**Roles:** {admin_roles}",
            inline=True
        )

        # TOS Settings
        embed.add_field(
            name="📋 TOS Settings",
            value="**Message:** Configured\n**Decline:** Configured",
            inline=True
        )

        # Bot Status Settings
        bot_status = config.get("bot_status", {})
        status_enabled = bot_status.get("enabled", True)
        activity_type = bot_status.get("activity_type", "watching")
        message = bot_status.get("message", "marketplace reviews")
        status_type = bot_status.get("status_type", "online")
        
        status_display = f"**Status:** {'✅ Enabled' if status_enabled else '❌ Disabled'}"
        if status_enabled:
            status_display += f"\n**Activity:** {activity_type.title()} {message}\n**Type:** {status_type.title()}"
        
        embed.add_field(
            name="🤖 Bot Status",
            value=status_display,
            inline=True
        )

        embed.set_footer(text="Use buttons to modify settings • Admin permissions required")
        embed.timestamp = datetime.now()

        return embed

    async def create_admin_settings_embed(self, interaction: discord.Interaction):
        config = load_config()
        
        embed = discord.Embed(
            title="👑 Admin Settings",
            description="Current administrative users and roles",
            color=discord.Color.purple()
        )

        # Admin Users
        admin_ids = config.get("admin_ids", [])
        if admin_ids:
            admin_mentions = []
            for admin_id in admin_ids[:10]:  # Limit to first 10
                member = interaction.guild.get_member(admin_id)
                if member:
                    admin_mentions.append(f"• {member.mention}")
                else:
                    admin_mentions.append(f"• <@{admin_id}> (Not found)")
            
            if len(admin_ids) > 10:
                admin_mentions.append(f"• ... and {len(admin_ids) - 10} more")
                
            embed.add_field(
                name=f"Admin Users ({len(admin_ids)})",
                value="\n".join(admin_mentions) if admin_mentions else "None",
                inline=False
            )

        # Admin Roles
        admin_role_ids = config.get("admin_role_ids", [])
        if admin_role_ids:
            role_mentions = []
            for role_id in admin_role_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(f"• {role.mention}")
                else:
                    role_mentions.append(f"• <@&{role_id}> (Role deleted)")
                    
            embed.add_field(
                name=f"Admin Roles ({len(admin_role_ids)})",
                value="\n".join(role_mentions) if role_mentions else "None",
                inline=False
            )

        if not admin_ids and not admin_role_ids:
            embed.description = "⚠️ No admins configured!"

        return embed


class AutoCloseSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Auto-Close Settings")
        
        config = load_config()
        
        self.enabled = discord.ui.TextInput(
            label="Enable Auto-Close (true/false)",
            placeholder="true or false",
            default=str(config.get("auto_close_enabled", True)).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.enabled)
        
        self.hours = discord.ui.TextInput(
            label="Auto-Close Hours (1-168)",
            placeholder="Number of hours before auto-close",
            default=str(config.get("auto_close_hours", 24)),
            max_length=3,
            required=True
        )
        self.add_item(self.hours)
        
        self.admin_confirmation = discord.ui.TextInput(
            label="Admin Close Confirmation (true/false)",
            placeholder="true or false",
            default=str(config.get("admin_close_confirmation", True)).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.admin_confirmation)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        
        # Validate enabled setting
        enabled_value = self.enabled.value.lower().strip()
        if enabled_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Enabled must be 'true' or 'false'", ephemeral=True)
        
        enabled = enabled_value == "true"
        
        # Validate hours
        try:
            hours = int(self.hours.value.strip())
            if not (1 <= hours <= 168):
                return await interaction.response.send_message("❌ Hours must be between 1 and 168", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Hours must be a valid number", ephemeral=True)

        # Validate admin confirmation setting
        admin_confirmation_value = self.admin_confirmation.value.lower().strip()
        if admin_confirmation_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Admin confirmation must be 'true' or 'false'", ephemeral=True)
        
        admin_confirmation = admin_confirmation_value == "true"

        # Save changes
        old_enabled = config.get("auto_close_enabled", True)
        old_hours = config.get("auto_close_hours", 24)
        old_admin_confirmation = config.get("admin_close_confirmation", True)
        
        config["auto_close_enabled"] = enabled
        config["auto_close_hours"] = hours
        config["admin_close_confirmation"] = admin_confirmation
        
        save_config(config)

        # Create response
        embed = discord.Embed(
            title="✅ Auto-Close Settings Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Enabled", value=f"{old_enabled} → **{enabled}**", inline=True)
        embed.add_field(name="Hours", value=f"{old_hours} → **{hours}**", inline=True)
        embed.add_field(name="Admin Confirmation", value=f"{old_admin_confirmation} → **{admin_confirmation}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log the changes
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="⚙️ Auto-Close Settings Modified",
                    description=f"{interaction.user.mention} updated auto-close settings",
                    color=discord.Color.blue()
                )
                log_embed.add_field(name="Enabled", value=f"{old_enabled} → {enabled}", inline=True)
                log_embed.add_field(name="Hours", value=f"{old_hours} → {hours}", inline=True)
                log_embed.add_field(name="Admin Confirmation", value=f"{old_admin_confirmation} → {admin_confirmation}", inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)


class TOSSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="TOS Settings")
        
        config = load_config()
        
        self.tos_message = discord.ui.TextInput(
            label="TOS Message",
            placeholder="Message shown when threads are created...",
            default=config.get("tos_message", ""),
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.tos_message)
        
        self.decline_response = discord.ui.TextInput(
            label="TOS Decline Response",
            placeholder="Message when TOS is declined...",
            default=config.get("tos_decline_response", ""),
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.decline_response)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        
        # Save changes
        config["tos_message"] = self.tos_message.value.strip()
        config["tos_decline_response"] = self.decline_response.value.strip()
        
        save_config(config)

        embed = discord.Embed(
            title="✅ TOS Settings Updated",
            description="Terms of Service messages have been updated",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log the changes
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="📋 TOS Settings Modified",
                    description=f"{interaction.user.mention} updated TOS messages",
                    color=discord.Color.blue()
                )
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)


class BotStatusSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Bot Status Settings")
        
        config = load_config()
        bot_status = config.get("bot_status", {})
        
        self.enabled = discord.ui.TextInput(
            label="Enable Custom Status (true/false)",
            placeholder="true or false",
            default=str(bot_status.get("enabled", True)).lower(),
            max_length=5,
            required=True
        )
        self.add_item(self.enabled)
        
        self.activity_type = discord.ui.TextInput(
            label="Activity Type",
            placeholder="playing, listening, watching, competing, streaming",
            default=bot_status.get("activity_type", "watching"),
            max_length=15,
            required=True
        )
        self.add_item(self.activity_type)
        
        self.message = discord.ui.TextInput(
            label="Status Message",
            placeholder="What the bot is doing (e.g. marketplace reviews)",
            default=bot_status.get("message", "marketplace reviews"),
            max_length=100,
            required=True
        )
        self.add_item(self.message)
        
        self.status_type = discord.ui.TextInput(
            label="Status Type",
            placeholder="online, idle, dnd, invisible",
            default=bot_status.get("status_type", "online"),
            max_length=10,
            required=True
        )
        self.add_item(self.status_type)

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        
        # Validate enabled setting
        enabled_value = self.enabled.value.lower().strip()
        if enabled_value not in ["true", "false"]:
            return await interaction.response.send_message("❌ Enabled must be 'true' or 'false'", ephemeral=True)
        
        enabled = enabled_value == "true"
        
        # Validate activity type
        valid_activities = ["playing", "listening", "watching", "competing", "streaming"]
        activity_type = self.activity_type.value.lower().strip()
        if activity_type not in valid_activities:
            return await interaction.response.send_message(
                f"❌ Activity type must be one of: {', '.join(valid_activities)}", 
                ephemeral=True
            )
        
        # Validate status type
        valid_statuses = ["online", "idle", "dnd", "invisible"]
        status_type = self.status_type.value.lower().strip()
        if status_type not in valid_statuses:
            return await interaction.response.send_message(
                f"❌ Status type must be one of: {', '.join(valid_statuses)}", 
                ephemeral=True
            )
        
        message = self.message.value.strip()
        if not message:
            return await interaction.response.send_message("❌ Status message cannot be empty", ephemeral=True)

        # Save changes
        old_bot_status = config.get("bot_status", {})
        config["bot_status"] = {
            "enabled": enabled,
            "activity_type": activity_type,
            "message": message,
            "status_type": status_type
        }
        
        save_config(config)

        # Update bot status immediately if enabled
        if enabled:
            await apply_bot_status(interaction.client, activity_type, message, status_type)

        # Create response
        embed = discord.Embed(
            title="✅ Bot Status Settings Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Enabled", value=f"**{enabled}**", inline=True)
        embed.add_field(name="Activity", value=f"**{activity_type.title()}**", inline=True)
        embed.add_field(name="Message", value=f"**{message}**", inline=True)
        embed.add_field(name="Status", value=f"**{status_type.title()}**", inline=True)
        
        if enabled:
            embed.add_field(name="Result", value=f"{activity_type.title()} {message}", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log the changes
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🤖 Bot Status Settings Modified",
                    description=f"{interaction.user.mention} updated bot status settings",
                    color=discord.Color.blue()
                )
                log_embed.add_field(name="Enabled", value=str(enabled), inline=True)
                log_embed.add_field(name="Activity", value=activity_type, inline=True)
                log_embed.add_field(name="Message", value=message, inline=True)
                log_embed.add_field(name="Status Type", value=status_type, inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
                
        print(f"[BOT-STATUS] {interaction.user} updated bot status: {activity_type} {message} ({status_type})")
