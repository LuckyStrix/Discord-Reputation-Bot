# bot.py - Entry point for Discord Forum Rep Bot
import asyncio
import os
import sys

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from utils.config import CONFIG_PATH, PROJECT_ROOT, load_config
from utils.db import init_db
from utils.presence import presence_from_config

# Console output contains emoji; don't crash when it is redirected to a file
# or a console that can't encode them (common on Windows).
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")

# Load environment variables from .env next to this file
load_dotenv(PROJECT_ROOT / ".env")

EXTENSIONS = ("cogs.logging_system", "cogs.reviews", "cogs.admin")

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True  # needed for the !sync prefix command
intents.members = True          # member cache for admin lists and the leaderboard


class RepBot(commands.Bot):
    async def setup_hook(self):
        init_db()
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        # Set the configured presence before connecting so it's sent on login
        activity, status = presence_from_config(load_config())
        if activity:
            self.activity = activity
            self.status = status


# Mentions are limited to users so text from config or user input can never
# ping @everyone/@here or roles.
bot = RepBot(
    command_prefix="!",
    intents=intents,
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
)


@bot.event
async def on_ready():
    """Called when the bot is ready (and again after reconnects)."""
    print(f"✅ Logged in as {bot.user}")
    print("✅ Ready. Use !sync to sync slash commands (or !sync guild for this server only).")


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context, scope: str = "global"):
    """
    Sync slash commands (bot owner only).

    !sync        - global sync (may take up to 1 hour to propagate)
    !sync guild  - instant sync to the current server only
    """
    try:
        if scope == "guild":
            if ctx.guild is None:
                return await ctx.send("❌ `!sync guild` must be used inside a server.")
            bot.tree.copy_global_to(guild=ctx.guild)
            synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Synced {len(synced)} slash commands to this server.")
        else:
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Globally synced {len(synced)} slash commands. (May take up to 1 hour to appear)")
        print(f"✅ Synced {len(synced)} slash commands ({scope}).")
    except Exception as e:
        print(f"[ERROR] Failed to sync commands: {e}")
        await ctx.send("❌ Failed to sync commands.")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    # Silently ignore unknown prefix commands and non-owners trying !sync
    if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
        return
    print(f"[ERROR] Command {ctx.command} failed: {error}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) if str(error) else "❌ You can't use this command here."
    else:
        print(f"[ERROR] /{interaction.command.name if interaction.command else '?'} failed: {error!r}")
        message = "❌ Something went wrong while running that command."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def check_setup() -> str | None:
    """Return the token, or None after explaining what's missing."""
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token.")
        return None
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} not found. Copy data/config.yaml.example to data/config.yaml and fill it in.")
        return None
    return token


async def main(token: str):
    # Route discord.py's own log messages (rate limits, gateway issues) to the console
    discord.utils.setup_logging()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    token = check_setup()
    if token is None:
        sys.exit(1)
    try:
        asyncio.run(main(token))
    except KeyboardInterrupt:
        pass
