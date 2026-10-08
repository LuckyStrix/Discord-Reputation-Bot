"""Terms-of-service prompt shown when a new marketplace post is created."""
import time

import discord

from utils import db
from utils.config import load_config
from views.review import post_review_ui

# Maps thread.id → timestamp when the TOS prompt was sent; messages posted
# after that are deleted until the prompt is answered.
pending_tos_timestamps: dict[int, float] = {}


class RepTOSView(discord.ui.View):
    def __init__(
        self,
        thread: discord.Thread,
        op_id: int,
        timeout: float = 30.0
    ):
        # timeout is in seconds
        super().__init__(timeout=timeout)
        self.thread = thread
        self.op_id = op_id

    @discord.ui.button(label='✅ I Agree', style=discord.ButtonStyle.success)
    async def agree(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.op_id:
            return await interaction.response.send_message(
                "Only the thread owner can accept the TOS.",
                ephemeral=True
            )

        # Stop the timeout and unblock the thread
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        # ─── Update the Thread Log with ✅ Accepted ───
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"TOS Status": f"✅ Accepted at <t:{int(time.time())}:T>"}
            )

        # Remove the TOS prompt and proceed to the review UI
        await interaction.message.delete()
        await post_review_ui(self.thread, self.op_id)

    @discord.ui.button(label='❌ I Do Not Agree', style=discord.ButtonStyle.danger)
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.op_id:
            return await interaction.response.send_message(
                "Only the thread owner can decline the TOS.",
                ephemeral=True
            )

        # Stop the timeout and unblock the thread
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        
        # ─── Update the Thread Log with ❌ Declined ───
        logging_cog = interaction.client.get_cog("LoggingSystem")
        if logging_cog:
            await logging_cog.update_thread_log(
                self.thread,
                field_updates={"TOS Status": f"❌ Declined at <t:{int(time.time())}:T>"}
            )

        config = load_config()
        # Edit the prompt to the decline response
        await interaction.message.edit(
            content=config['tos_decline_response'],
            view=None
        )

        # Archive & lock the thread
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

    async def on_timeout(self):
        # Called if neither button is pressed within timeout
        self.stop()
        pending_tos_timestamps.pop(self.thread.id, None)

        try:
            print(f"[TOS] Thread {self.thread.id} timed out. Auto-closing.")

            # ─── Update the Thread Log to show ❌ Timed Out ───
            bot = self.thread._state._get_client()
            logging_cog = bot.get_cog("LoggingSystem")
            if logging_cog:
                await logging_cog.update_thread_log(
                    self.thread,
                    field_updates={
                        "TOS Status": f"⌛ Timed out at <t:{int(time.time())}:T>",
                        "Thread Status": f"❌ Closed (timeout)"
                    }
                )

            # Notify in-thread
            await self.thread.send(
                "⏱️ No response to TOS in time. This post has been auto-closed."
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

        except Exception as e:
            print(f"[ERROR] Auto-close on timeout failed: {e}")
