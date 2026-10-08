# bot.py - Entry point for Discord Forum Rep Bot
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from utils.db import init_db
from views.review import ReviewButtonView
from views.tos import RepTOSView

# Load environment variables from .env
load_dotenv()

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

# Initialize bot. Mentions are limited to users so text from config or
# user input can never ping @everyone/@here or roles.
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
)

@bot.event
async def on_ready():
    """
    Called when the bot is ready. Initializes the database,
    registers persistent views, and prints startup confirmation.
    """
    print(f"✅ Logged in as {bot.user}")
    init_db()

    # Register persistent views for button survival
    bot.add_view(ReviewButtonView())
    bot.add_view(RepTOSView())

    print("✅ Ready. Use !sync to globally sync slash commands.")

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

async def main():
    """
    Main entrypoint for loading cogs and starting the bot.
    """
    async with bot:
        await bot.load_extension("cogs.logging_system")
        await bot.load_extension("cogs.reviews")
        await bot.load_extension("cogs.admin")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
