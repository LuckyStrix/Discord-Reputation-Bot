"""Review cog: forum post lifecycle, review lookups and the auto-close task."""
import asyncio
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import db
from utils.checks import is_admin
from utils.config import load_config
from utils.formatting import generate_star_rating, review_stars, star_bar
from utils.presence import apply_bot_status
from views.review import AutoCloseView, ReviewButtonView, post_review_ui
from views.tos import RepTOSView, pending_tos_timestamps


class Reviews(commands.Cog):
    """Forum post lifecycle, review commands and the auto-close background task."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("🔧 Rep cog loaded")

    async def cog_load(self):
        """Start background tasks when the cog loads"""
        self.auto_close_task.start()
        
        # Initialize bot status from config
        await self.initialize_bot_status()

    async def initialize_bot_status(self):
        """Initialize bot status from configuration on startup"""
        try:
            config = load_config()
            bot_status = config.get("bot_status", {})
            
            if bot_status.get("enabled", True):
                activity_type = bot_status.get("activity_type", "watching")
                message = bot_status.get("message", "marketplace reviews")
                status_type = bot_status.get("status_type", "online")
                
                await apply_bot_status(self.bot, activity_type, message, status_type)
            else:
                print("[BOT-STATUS] Custom status disabled in config")
                
        except Exception as e:
            print(f"[ERROR] Failed to initialize bot status: {e}")

    async def cog_unload(self):
        """Stop background tasks when the cog unloads"""
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)  # Check every 10 minutes
    async def auto_close_task(self):
        """Background task to auto-close threads that have passed their scheduled time"""
        try:
            threads_to_close = db.get_threads_to_auto_close()
            
            if threads_to_close:
                print(f"[AUTO-CLOSE] Found {len(threads_to_close)} thread(s) ready for auto-close")
            
            for thread_data in threads_to_close:
                try:
                    # Get the actual thread object
                    channel = self.bot.get_channel(thread_data['channel_id'])
                    if not channel:
                        continue
                        
                    thread = channel.get_thread(thread_data['thread_id'])
                    if not thread:
                        continue
                    
                    # Send auto-close notification
                    embed = discord.Embed(
                        title="🔒 Thread Auto-Closed",
                        description="This thread was automatically closed 24 hours after receiving its first review.",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Why did this happen?",
                        value="To keep the marketplace clean, threads automatically close after receiving reviews. This helps prevent clutter from completed transactions.",
                        inline=False
                    )
                    
                    await thread.send(embed=embed)
                    
                    # Update thread log
                    logging_cog = self.bot.get_cog("LoggingSystem")
                    if logging_cog:
                        await logging_cog.update_thread_log(
                            thread,
                            field_updates={"Thread Status": f"🤖 Auto-closed at <t:{int(time.time())}:T>"}
                        )
                    
                    # Archive and lock the thread
                    await thread.edit(archived=True, locked=True)
                    
                    # Update thread status in database
                    db.upsert_thread(
                        thread_id=thread.id,
                        channel_id=thread.parent_id,
                        guild_id=thread.guild.id,
                        name=thread.name,
                        owner_id=thread.owner_id,
                        jump_url=thread.jump_url,
                        archived=True,
                        locked=True
                    )
                    
                    # Log to log channel
                    config = load_config()
                    log_ch_id = config.get("log_channel")
                    if log_ch_id:
                        log_ch = self.bot.get_channel(log_ch_id)
                        if log_ch:
                            log_embed = discord.Embed(
                                title="🤖 Thread Auto-Closed",
                                description=f"Thread [{thread.name}]({thread.jump_url}) was automatically closed",
                                color=discord.Color.red()
                            )
                            log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
                            log_embed.add_field(name="Reason", value="24-hour timer expired", inline=True)
                            log_embed.add_field(name="Action", value="Archived & Locked", inline=True)
                            log_embed.timestamp = datetime.now()
                            await log_ch.send(embed=log_embed)
                    
                    print(f"[AUTO-CLOSE] Successfully closed thread {thread.id} ({thread.name})")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to auto-close thread {thread_data['thread_id']}: {e}")
                    
        except Exception as e:
            print(f"[ERROR] Auto-close task failed: {e}")

    @auto_close_task.before_loop
    async def before_auto_close_task(self):
        """Wait until the bot is ready before starting the auto-close task"""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        try:
            config = load_config()
            forums = [int(f) for f in config.get("forums", []) if str(f).isdigit()]
            if thread.parent_id not in forums:
                return

            # Save thread information to database
            db.upsert_thread(
                thread_id=thread.id,
                channel_id=thread.parent_id,
                guild_id=thread.guild.id,
                name=thread.name,
                owner_id=thread.owner_id,
                jump_url=thread.jump_url,
                archived=thread.archived,
                locked=thread.locked
            )

            # Join so the bot can send
            try:
                await thread.join()
            except Exception:
                pass

            # Prepare TOS prompt
            timeout_secs = 30
            ts = int(time.time()) + timeout_secs
            countdown = f"<t:{ts}:R>"
            tos_message_text = config["tos_message"].replace("{timeout}", countdown)
            
            # Create embedded TOS message
            embed = discord.Embed(
                title="📋 Marketplace Terms of Service",
                description=tos_message_text,
                color=discord.Color.blue()
            )
            
            view = RepTOSView(thread=thread, op_id=thread.owner_id, timeout=timeout_secs)
            await asyncio.sleep(2)
            await thread.send(content=f"<@{thread.owner_id}>", embed=embed, view=view)
            pending_tos_timestamps[thread.id] = time.time()

            # Initialize log embed
            logging_cog = self.bot.get_cog("LoggingSystem")
            if logging_cog:
                await logging_cog.create_thread_log(
                    thread,
                    fields={
                        "TOS Status": "⏳ Pending",
                        "Review Events": "*No events yet*",
                        "Thread Status": "✅ Open"
                    }
                )

        except Exception as e:
            print(f"[ERROR] on_thread_create: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Delete user messages posted after TOS prompt until it's handled
        ts = pending_tos_timestamps.get(message.channel.id)
        if (
            ts
            and isinstance(message.channel, discord.Thread)
            and not message.author.bot
            and message.created_at.timestamp() > ts
        ):
            try:
                await message.delete()
            except discord.Forbidden:
                pass

    @app_commands.command(name="reviews", description="Check a user's reviews and rating.")
    @app_commands.describe(user="The user to check reviews for.")
    async def reviews_lookup(self, interaction: discord.Interaction, user: discord.Member):
        avg_rating, total_reviews, latest_reviews = db.get_user_reviews(user.id)
        
        embed = discord.Embed(
            title=f"⭐ Reviews for {user.display_name}",
            color=discord.Color.blue()
        )
        
        if total_reviews == 0:
            embed.description = "😶 No reviews yet. Time to build that reputation!"
            embed.add_field(name="Rating", value="No rating yet", inline=True)
            embed.add_field(name="Total Reviews", value="0", inline=True)
        else:
            rating_display = generate_star_rating(avg_rating, total_reviews)
            embed.description = rating_display
            embed.add_field(name="Average Rating", value=f"{avg_rating:.1f}/10", inline=True)
            embed.add_field(name="Total Reviews", value=str(total_reviews), inline=True)
            
            # Show latest reviews
            if latest_reviews:
                reviews_text = ""
                for i, review in enumerate(latest_reviews):
                    stars = review_stars(review['rating'])
                    reviews_text += f"**{stars} {review['rating']}/10** by <@{review['giver_id']}>"
                    if review['notes']:
                        notes_preview = review['notes'][:80] + "..." if len(review['notes']) > 80 else review['notes']
                        reviews_text += f"\n> {notes_preview}"
                    if i < len(latest_reviews) - 1:
                        reviews_text += "\n\n"
                
                embed.add_field(name="Latest Reviews", value=reviews_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 users by rating.")
    async def review_leaderboard(self, interaction: discord.Interaction):
        top = db.get_top_rated_users(limit=10)
        embed = discord.Embed(
            title="🏆 Top Rated Users",
            description="Here are the highest rated users:",
            color=discord.Color.gold()
        )
        if not top:
            embed.description = "No review data found."
        else:
            for i, (user_id, avg_rating, total_reviews) in enumerate(top, start=1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"<@{user_id}>"
                
                stars = star_bar(avg_rating)
                embed.add_field(
                    name=f"{i}. {name}",
                    value=f"{stars} {avg_rating:.1f}/10 ({total_reviews} review{'s' if total_reviews != 1 else ''})",
                    inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @app_commands.command(name="send_review_ui", description="Send the rate/close interface to the current thread (admin only).")
    async def send_review_ui(self, interaction: discord.Interaction):
        # Check if user is admin
        if not is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ Only admins can use this command.", ephemeral=True
            )
            return
        
        # Check if command is used in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ This command can only be used in a thread.", ephemeral=True
            )
            return
        
        thread = interaction.channel
        op_id = thread.owner_id
        
        # Send the review UI
        await post_review_ui(thread, op_id)
        
        await interaction.response.send_message(
            "✅ Rate/close interface sent to this thread.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    # Persistent views keep buttons working after a restart
    bot.add_view(ReviewButtonView())
    bot.add_view(AutoCloseView(None))
    await bot.add_cog(Reviews(bot))
