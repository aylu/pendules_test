import asyncio
import json
import logging
from datetime import UTC

import discord
from sqlalchemy import select

from app.core.config import settings
from app.db.models import DiscordMessage
from app.db.session import SessionLocal

logger = logging.getLogger("discord_ingestor")


intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True


class DiscordIngestor(discord.Client):
    async def on_ready(self):
        logger.info("Bot connecté en tant que %s", self.user)

    async def on_message(self, message: discord.Message):
        if message.author.bot and message.author.id == self.user.id:
            return
        if settings.discord_guild_id and (message.guild is None or message.guild.id != settings.discord_guild_id):
            return
        if settings.channel_id_list and message.channel.id not in settings.channel_id_list:
            return

        with SessionLocal() as db:
            entity = db.get(DiscordMessage, str(message.id))
            if entity is None:
                entity = DiscordMessage(message_id=str(message.id))

            entity.guild_id = int(message.guild.id) if message.guild else 0
            entity.channel_id = int(message.channel.id)
            entity.author_id = int(message.author.id)
            entity.author_name = str(message.author)
            entity.content = message.content or ""
            entity.created_at = message.created_at.replace(tzinfo=UTC)
            entity.edited_at = message.edited_at.replace(tzinfo=UTC) if message.edited_at else None
            entity.deleted = False
            entity.attachment_count = len(message.attachments)
            entity.embed_count = len(message.embeds)
            entity.raw_json = json.dumps(message.to_dict(), default=str)

            db.merge(entity)
            db.commit()

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.on_message(after)

    async def on_message_delete(self, message: discord.Message):
        with SessionLocal() as db:
            entity = db.get(DiscordMessage, str(message.id))
            if entity:
                entity.deleted = True
                db.commit()


async def run() -> None:
    if not settings.discord_bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")

    client = DiscordIngestor(intents=intents)
    await client.start(settings.discord_bot_token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
