"""Keeps one log-channel embed per marketplace thread up to date."""
import time
from typing import Any, Dict, Optional

import discord
from discord.ext import commands

from utils import db
from utils.config import load_config

# Discord rejects embed field values longer than this
FIELD_LIMIT = 1024
EMPTY_EVENTS = "*No events yet*"


class LoggingSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("📋 Logging system loaded")

    async def get_log_channel(self) -> Optional[discord.TextChannel]:
        config = load_config()
        log_ch_id = config.get("log_channel")
        if not log_ch_id:
            return None
        log_ch = self.bot.get_channel(log_ch_id)
        if not log_ch:
            print(f"[WARN] log_channel {log_ch_id} not found")
            return None
        return log_ch

    async def _fetch_thread_log(self, log_ch: discord.TextChannel, thread_id: int) -> Optional[discord.Message]:
        """Fetch this thread's existing log message, using the ID stored in the database."""
        info = db.get_thread_info(thread_id)
        if not info or not info.get("log_message_id"):
            return None
        try:
            return await log_ch.fetch_message(info["log_message_id"])
        except (discord.NotFound, discord.Forbidden):
            return None

    async def create_thread_log(
        self,
        thread: discord.Thread,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[discord.Color] = None,
        fields: Optional[Dict[str, str]] = None
    ) -> Optional[discord.Message]:
        log_ch = await self.get_log_channel()
        if not log_ch:
            return None

        existing = await self._fetch_thread_log(log_ch, thread.id)
        if existing:
            return existing

        # Embed titles can't contain links, so the link goes in the description
        embed = discord.Embed(
            title=title or f"📋 Thread: {thread.name}"[:256],
            description=description or f"[Open thread]({thread.jump_url}) • Created by <@{thread.owner_id}>",
            color=color or discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        if fields:
            for name, value in fields.items():
                embed.add_field(name=name, value=value, inline=False)
        else:
            embed.add_field(name="Thread Status", value="✅ Open", inline=False)
            embed.add_field(name="Review Events", value=EMPTY_EVENTS, inline=False)

        msg = await log_ch.send(embed=embed)
        db.set_thread_log_message(thread.id, msg.id)
        return msg

    async def update_thread_log(
        self,
        thread: discord.Thread,
        field_updates: Optional[Dict[str, str]] = None,
        event_additions: Optional[Dict[str, str]] = None,
        embed_updates: Optional[Dict[str, Any]] = None
    ):
        log_ch = await self.get_log_channel()
        if not log_ch:
            return

        msg = await self._fetch_thread_log(log_ch, thread.id)
        if not msg:
            msg = await self.create_thread_log(thread)
        if not msg or not msg.embeds:
            return

        embed = msg.embeds[0]
        embed.timestamp = discord.utils.utcnow()

        if embed_updates:
            if "title" in embed_updates:
                embed.title = embed_updates["title"]
            if "description" in embed_updates:
                embed.description = embed_updates["description"]
            if "color" in embed_updates:
                embed.color = embed_updates["color"]

        if field_updates:
            for field_name, field_value in field_updates.items():
                self._set_field(embed, field_name, field_value)

        if event_additions:
            # Events are appended to the field's current text, which lives in
            # Discord, so history survives bot restarts.
            for field_name, event in event_additions.items():
                line = f"{event} at <t:{int(time.time())}:T>"
                current = next((f.value for f in embed.fields if f.name == field_name), None)
                if not current or current == EMPTY_EVENTS:
                    value = line
                else:
                    value = f"{current}\n{line}"
                # Keep the newest events if the field would overflow
                while len(value) > FIELD_LIMIT and "\n" in value:
                    value = value.split("\n", 1)[1]
                self._set_field(embed, field_name, value[-FIELD_LIMIT:])

        try:
            await msg.edit(embed=embed)
        except discord.HTTPException as e:
            print(f"[WARN] Could not update thread log for {thread.id}: {e}")

    @staticmethod
    def _set_field(embed: discord.Embed, name: str, value: str) -> None:
        for i, field in enumerate(embed.fields):
            if field.name == name:
                embed.set_field_at(i, name=name, value=value, inline=False)
                return
        embed.add_field(name=name, value=value, inline=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(LoggingSystem(bot))
