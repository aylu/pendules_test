import asyncio
import json
import logging
from datetime import UTC

import discord

from app.core.config import settings
from app.db.base import Base
from app.db.models import DiscordMessage
from app.db.session import SessionLocal, engine

logger = logging.getLogger("discord_backfill")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True


class BackfillClient(discord.Client):
    async def on_ready(self):
        logger.info("Connecté : %s", self.user)
        Base.metadata.create_all(bind=engine)

        channel_ids = settings.channel_id_list
        if not channel_ids:
            logger.warning("Aucun DISCORD_CHANNEL_IDS défini.")
            await self.close()
            return

        for channel_id in channel_ids:
            channel = self.get_channel(channel_id)
            if channel is None:
                logger.warning("Salon introuvable: %s", channel_id)
                continue
            logger.info("Backfill salon %s", channel_id)
            inserted = 0
            async for message in channel.history(limit=None, oldest_first=True):
                with SessionLocal() as db:
                    existing = db.get(DiscordMessage, str(message.id))
                    if existing:
                        continue

                    row = DiscordMessage(
                        message_id=str(message.id),
                        guild_id=int(message.guild.id) if message.guild else 0,
                        channel_id=int(message.channel.id),
                        author_id=int(message.author.id),
                        author_name=str(message.author),
                        content=message.content or "",
                        created_at=message.created_at.replace(tzinfo=UTC),
                        edited_at=message.edited_at.replace(tzinfo=UTC) if message.edited_at else None,
                        deleted=False,
                        attachment_count=len(message.attachments),
                        embed_count=len(message.embeds),
                        raw_json=json.dumps(message.to_dict(), default=str),
                    )
                    db.add(row)
                    db.commit()
                    inserted += 1
            logger.info("Salon %s terminé: %s messages insérés", channel_id, inserted)

        await self.close()


async def main() -> None:
    if not settings.discord_bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")

    client = BackfillClient(intents=intents)
    await client.start(settings.discord_bot_token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
