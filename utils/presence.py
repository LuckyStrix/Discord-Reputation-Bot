"""Applies the configurable bot status (activity + online status)."""
import discord

STATUS_TYPES = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "invisible": discord.Status.invisible,
}

ACTIVITY_TYPES = {
    "playing": discord.ActivityType.playing,
    "listening": discord.ActivityType.listening,
    "watching": discord.ActivityType.watching,
    "competing": discord.ActivityType.competing,
    "streaming": discord.ActivityType.streaming,
}


async def apply_bot_status(bot, activity_type: str, message: str, status_type: str):
    """Update the bot's Discord presence."""
    try:
        status = STATUS_TYPES.get(status_type, discord.Status.online)
        activity_enum = ACTIVITY_TYPES.get(activity_type, discord.ActivityType.watching)

        if activity_type == "streaming":
            # Streaming requires a URL (using a placeholder)
            activity = discord.Streaming(name=message, url="https://twitch.tv/placeholder")
        else:
            activity = discord.Activity(type=activity_enum, name=message)

        await bot.change_presence(status=status, activity=activity)
        print(f"[BOT-STATUS] Updated bot status: {activity_type} {message} ({status_type})")

    except Exception as e:
        print(f"[ERROR] Failed to update bot status: {e}")
