"""In-thread review UI: review button, review modal, close flow and auto-close notice."""
import random
import sqlite3
import time
from datetime import datetime

import discord

from utils import db
from utils.checks import is_admin
from utils.config import load_config
from utils.formatting import generate_star_rating, review_stars
from utils.messages import load_rep_messages


def is_thread_closed(thread: discord.abc.GuildChannel) -> bool:
    """
    True if the post has been closed. Buttons in locked/archived threads still
    fire interactions, so every review/close action must check this.
    """
    if getattr(thread, "locked", False) or getattr(thread, "archived", False):
        return True
    info = db.get_thread_info(thread.id)
    return bool(info and (info["locked"] or info["archived"]))


async def _reject_if_not_open_thread(interaction: discord.Interaction) -> bool:
    """Reply and return True if this interaction isn't in an open forum post."""
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("❌ This only works inside a forum post.", ephemeral=True)
        return True
    if is_thread_closed(interaction.channel):
        await interaction.response.send_message("🔒 This post is closed.", ephemeral=True)
        return True
    return False


class AutoCloseView(discord.ui.View):
    def __init__(self, thread: discord.Thread = None):
        super().__init__(timeout=None)
        self.thread = thread

    @discord.ui.button(custom_id="cancel_auto_close", label="I have multiple items - Keep thread open", style=discord.ButtonStyle.secondary)
    async def cancel_auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get thread from interaction if not provided during init (persistent view)
        thread = self.thread or interaction.channel
        
        # Only the thread owner can cancel auto-close
        if interaction.user.id != thread.owner_id:
            return await interaction.response.send_message(
                "Only the thread owner can cancel auto-close.", ephemeral=True
            )
        
        # Cancel the auto-close in database
        db.cancel_thread_auto_close(thread.id)
        
        # Update the message to show it's been cancelled
        embed = discord.Embed(
            title="🔓 Auto-close Cancelled",
            description="This thread will no longer be automatically closed. You can close it manually when ready.",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Log the cancellation
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🔓 Auto-Close Cancelled",
                    description=f"{interaction.user.mention} cancelled auto-close for [{thread.name}]({thread.jump_url})",
                    color=discord.Color.green()
                )
                log_embed.add_field(name="Thread Owner", value=f"<@{thread.owner_id}>", inline=True)
                log_embed.add_field(name="Reason", value="Multiple items in listing", inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
                
        print(f"[AUTO-CLOSE] {interaction.user} cancelled auto-close for thread {thread.id} ({thread.name})")


class ReviewModal(discord.ui.Modal):
    def __init__(self, thread: discord.Thread, receiver_id: int):
        super().__init__(title="Leave a Review")
        self.thread = thread
        self.receiver_id = receiver_id
        
        self.rating = discord.ui.TextInput(
            label="Rating (1-10)",
            placeholder="Enter a number between 1 and 10",
            required=True,
            max_length=2
        )
        self.add_item(self.rating)
        
        self.notes = discord.ui.TextInput(
            label="Review Notes (Optional)",
            placeholder="Share your experience... (optional)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.notes)
    
    async def on_submit(self, interaction: discord.Interaction):
        # The post may have been closed while the modal was open
        if is_thread_closed(self.thread):
            return await interaction.response.send_message("🔒 This post is closed.", ephemeral=True)

        try:
            rating_value = int(self.rating.value)
            if not (1 <= rating_value <= 10):
                raise ValueError("Rating must be between 1 and 10")
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid rating between 1 and 10.", 
                ephemeral=True
            )
            return
        
        notes_value = self.notes.value.strip() if self.notes.value else None
        
        # Record the review
        success = db.add_review(
            interaction.user.id,
            self.receiver_id,
            self.thread.id,
            rating_value,
            notes_value
        )
        
        if not success:
            await interaction.response.send_message(
                "❌ You've already reviewed this user in this thread.", 
                ephemeral=True
            )
            return
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Review Submitted",
            description=(
                f"{interaction.user.mention} gave a **{rating_value}/10** rating "
                f"to <@{self.receiver_id}> in [this thread]({self.thread.jump_url})"
            ),
            color=discord.Color.green()
        )
        
        if notes_value:
            embed.add_field(name="Review Notes", value=notes_value[:100] + "..." if len(notes_value) > 100 else notes_value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Check if this is the first review in the thread
        is_first = db.is_first_review_in_thread(self.thread.id)
        
        # Send mention to thread owner with review notification
        mention_message = f"<@{self.receiver_id}> You received a **{rating_value}/10** review!"
        
        # Load config to check auto-close settings
        config = load_config()
        auto_close_enabled = config.get("auto_close_enabled", True)
        
        if is_first and auto_close_enabled:
            # Schedule auto-close based on configured hours
            auto_close_hours = config.get("auto_close_hours", 24)
            close_time = time.time() + (auto_close_hours * 60 * 60)  # Convert hours to seconds
            db.schedule_thread_auto_close(self.thread.id, close_time)
            
            # Create auto-close warning embed
            auto_close_embed = discord.Embed(
                title="⏰ Auto-Close Scheduled",
                description=f"This thread will automatically close <t:{int(close_time)}:R> unless you cancel it below.",
                color=discord.Color.orange()
            )
            auto_close_embed.add_field(
                name="Why?", 
                value="Threads auto-close after the first review to keep the marketplace clean. If you have multiple items in this listing, click the button below.",
                inline=False
            )
            
            view = AutoCloseView(self.thread)
            await self.thread.send(content=mention_message, embed=auto_close_embed, view=view)
            
            # Log auto-close scheduling
            log_ch_id = config.get("log_channel")
            if log_ch_id:
                log_ch = interaction.client.get_channel(log_ch_id)
                if log_ch:
                    log_embed = discord.Embed(
                        title="⏰ Auto-Close Scheduled",
                        description=f"Thread [{self.thread.name}]({self.thread.jump_url}) scheduled to auto-close <t:{int(close_time)}:R>",
                        color=discord.Color.orange()
                    )
                    log_embed.add_field(name="Thread Owner", value=f"<@{self.receiver_id}>", inline=True)
                    log_embed.add_field(name="Trigger", value="First review received", inline=True)
                    log_embed.add_field(name="Timer", value=f"{auto_close_hours} hours", inline=True)
                    log_embed.timestamp = datetime.now()
                    await log_ch.send(embed=log_embed)
                    
            print(f"[AUTO-CLOSE] Scheduled thread {self.thread.id} ({self.thread.name}) to close in {auto_close_hours} hours")
        else:
            # Just send the mention for subsequent reviews or when auto-close is disabled
            await self.thread.send(content=mention_message)
            
            # Log if auto-close is disabled but would have been triggered
            if is_first and not auto_close_enabled:
                print(f"[AUTO-CLOSE] First review in thread {self.thread.id} but auto-close is disabled")
        
        # Update thread log
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                event_additions={
                    "Review Events": f"{interaction.user.mention} gave {rating_value}/10 rating"
                }
            )
        
        # Send to log channel if configured
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                await log_ch.send(embed=embed)
        
        # Refresh the in-thread review UI
        await post_review_ui(self.thread, self.receiver_id)


class CloseConfirmationModal(discord.ui.Modal):
    def __init__(self, thread: discord.Thread):
        super().__init__(title="Close Post Confirmation")
        self.thread = thread
        
        self.confirmation = discord.ui.TextInput(
            label="Type 'Yes' to confirm closing without reviews",
            placeholder="Yes",
            required=True,
            max_length=3
        )
        self.add_item(self.confirmation)
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.lower() != "yes":
            await interaction.response.send_message(
                "❌ Post closure cancelled. You must type 'Yes' to confirm.",
                ephemeral=True
            )
            return
        
        # Proceed with closing the post
        await interaction.response.send_message(
            "🔒 This thread is now closed by its creator (no reviews received).", 
            ephemeral=False
        )
        
        # Update thread log
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"Thread Status": f"❌ Closed without reviews at <t:{int(time.time())}:T>"}
            )
        
        # Archive & lock
        await self.thread.edit(archived=True, locked=True)
        
        # Update thread status in database
        db.upsert_thread(
            thread_id=self.thread.id,
            channel_id=self.thread.parent_id,
            guild_id=self.thread.guild.id,
            name=self.thread.name,
            owner_id=self.thread.owner_id,
            jump_url=self.thread.jump_url,
            archived=True,
            locked=True
        )


class AdminCloseConfirmationModal(discord.ui.Modal):
    def __init__(self, thread: discord.Thread, admin_user: discord.Member):
        super().__init__(title="Admin Close Post Confirmation")
        self.thread = thread
        self.admin_user = admin_user
        
        self.confirmation = discord.ui.TextInput(
            label="Type 'Yes' to confirm admin closure",
            placeholder="Yes",
            required=True,
            max_length=3
        )
        self.add_item(self.confirmation)
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value.lower() != "yes":
            await interaction.response.send_message(
                "❌ Admin closure cancelled. You must type 'Yes' to confirm.",
                ephemeral=True
            )
            return
        
        # Proceed with admin closing the post
        closure_message = f"🔒 This thread has been closed by admin {self.admin_user.mention}."
        log_status = f"❌ Force closed by admin {self.admin_user.mention} at <t:{int(time.time())}:T>"
        
        await interaction.response.send_message(closure_message, ephemeral=False)
        
        # Update thread log
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"Thread Status": log_status}
            )
        
        # Archive & lock
        await self.thread.edit(archived=True, locked=True)
        
        # Update thread status in database
        db.upsert_thread(
            thread_id=self.thread.id,
            channel_id=self.thread.parent_id,
            guild_id=self.thread.guild.id,
            name=self.thread.name,
            owner_id=self.thread.owner_id,
            jump_url=self.thread.jump_url,
            archived=True,
            locked=True
        )
        
        # Log admin closure
        config = load_config()
        log_ch_id = config.get("log_channel")
        if log_ch_id:
            log_ch = interaction.client.get_channel(log_ch_id)
            if log_ch:
                log_embed = discord.Embed(
                    title="🔒 Admin Force Close",
                    description=f"{self.admin_user.mention} force-closed thread [{self.thread.name}]({self.thread.jump_url})",
                    color=discord.Color.red()
                )
                log_embed.add_field(name="Thread Owner", value=f"<@{self.thread.owner_id}>", inline=True)
                log_embed.add_field(name="Action", value="Force closed by admin", inline=True)
                log_embed.timestamp = datetime.now()
                await log_ch.send(embed=log_embed)
        
        print(f"[ADMIN-CLOSE] {self.admin_user} force-closed thread {self.thread.id} ({self.thread.name})")


async def post_review_ui(thread: discord.Thread, op_id: int):
    config = load_config()
    rep_msgs = load_rep_messages()
    no_rep_lines = config.get("no_rep_messages", [])

    # Get review data instead of old rep data
    avg_rating, total_reviews, latest_reviews = db.get_user_reviews(op_id)

    # 1) No reviews yet
    if total_reviews == 0:
        content = f"😶 {random.choice(no_rep_lines)}"
        gif_url = None

    # 2) Otherwise pick a line based on average rating
    else:
        if avg_rating >= 7.0:
            pool = rep_msgs["good"]
        elif avg_rating <= 4.0:
            pool = rep_msgs["bad"]
        else:
            pool = rep_msgs["neutral"]

        raw = random.choice(pool) if pool else ""
        # Split on last space
        parts = raw.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].lower().endswith((".gif", ".mp4", ".webm")):
            text, gif_url = parts[0], parts[1]
        else:
            text, gif_url = raw, None

        content = text

    # 3) Prepend star rating if any
    rating_display = generate_star_rating(avg_rating, total_reviews)
    if rating_display and total_reviews > 0:
        content = f"📊 {rating_display}\n\n{content}"

    # 4) Build the embed
    embed = discord.Embed(description=content, color=discord.Color.green())
    if gif_url:
        embed.set_image(url=gif_url)
        print(f"[DEBUG] Embedding GIF: {gif_url}")  # for your logs

    # 5) Add latest reviews if any
    if latest_reviews:
        reviews_text = ""
        for i, review in enumerate(latest_reviews[:3]):
            stars = review_stars(review['rating'])
            reviews_text += f"**{stars} {review['rating']}/10** by <@{review['giver_id']}>"
            if review['notes']:
                notes_preview = review['notes'][:50] + "..." if len(review['notes']) > 50 else review['notes']
                reviews_text += f"\n> {notes_preview}"
            reviews_text += "\n\n"
        
        embed.add_field(name="📝 Latest Reviews", value=reviews_text.strip(), inline=False)

    view = ReviewButtonView()
    await thread.send(embed=embed, view=view)


class ReviewButtonView(discord.ui.View):
    def __init__(self):
        # persistent across restarts
        super().__init__(timeout=None)

    @discord.ui.button(custom_id="leave_review", label="⭐ Leave a Review", style=discord.ButtonStyle.primary)
    async def leave_review(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _reject_if_not_open_thread(interaction):
            return
        thread: discord.Thread = interaction.channel
        op_id = thread.owner_id

        # 1) Prevent self-review
        if interaction.user.id == op_id:
            return await interaction.response.send_message(
                "You can't review yourself.", ephemeral=True
            )

        # 2) Check if already reviewed
        if db.has_user_reviewed(interaction.user.id, op_id, thread.id):
            return await interaction.response.send_message(
                "You've already reviewed this user in this thread.", ephemeral=True
            )

        # 3) Require the user to have spoken in the thread
        has_spoken = False
        async for msg in thread.history(limit=100):
            if msg.author.id == interaction.user.id:
                has_spoken = True
                break
        if not has_spoken:
            return await interaction.response.send_message(
                "You need to interact in the thread first before leaving a review.", ephemeral=True
            )

        # 4) Show the review modal
        modal = ReviewModal(thread, op_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(custom_id="close_post", label="Close Post", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await _reject_if_not_open_thread(interaction):
            return
        thread: discord.Thread = interaction.channel
        op_id = thread.owner_id
        
        # Check if user is OP or admin
        is_owner = interaction.user.id == op_id
        is_user_admin = is_admin(interaction.user)
        
        # 1) Only the OP or admins may close
        if not is_owner and not is_user_admin:
            return await interaction.response.send_message(
                "Only the thread creator or admins can close this post.", ephemeral=True
            )

        # 2) Check for admin confirmation setting
        config = load_config()
        admin_confirmation_enabled = config.get("admin_close_confirmation", True)
        
        # Admin users - check if confirmation is required
        if is_user_admin and not is_owner:
            if admin_confirmation_enabled:
                modal = AdminCloseConfirmationModal(thread, interaction.user)
                await interaction.response.send_modal(modal)
                return
            else:
                # Direct admin close without confirmation
                closure_message = f"🔒 This thread has been closed by admin {interaction.user.mention}."
                log_status = f"❌ Force closed by admin {interaction.user.mention} at <t:{int(time.time())}:T>"
                
                await interaction.response.send_message(closure_message, ephemeral=False)
                
                # Update thread log
                logging_cog = interaction.client.get_cog("LoggingSystem")
                if logging_cog:
                    await logging_cog.update_thread_log(
                        thread,
                        field_updates={"Thread Status": log_status}
                    )
                
                # Archive & lock
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
                return

        # 3) For thread owner (OP), check if there's at least one review
        if is_owner:
            conn = sqlite3.connect(db.DB_PATH)
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM reviews WHERE thread_id = ? AND giver_id != ?",
                (thread.id, op_id)
            )
            count = c.fetchone()[0]
            conn.close()

            # If no reviews, show confirmation modal
            if count == 0:
                modal = CloseConfirmationModal(thread)
                await interaction.response.send_modal(modal)
                return

        # 4) Thread owner closing with reviews (direct close)
        closure_message = "🔒 This thread is now closed by its creator."
        log_status = f"❌ Closed at <t:{int(time.time())}:T>"
        
        await interaction.response.send_message(closure_message, ephemeral=False)

        # 5) Update thread log to Closed
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                thread,
                field_updates={"Thread Status": log_status}
            )

        # 6) Archive & lock
        await thread.edit(archived=True, locked=True)
        
        # 7) Update thread status in database
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
