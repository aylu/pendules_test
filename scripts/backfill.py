import asyncio
import json
import logging
from datetime import UTC

import discord

from app.core.config import settings
from app.db.base import Base
from app.db.models import DiscordMessage
from app.db.session import SessionLocal, engine

# Configuration de base des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord_backfill")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True


def message_to_dict(message: discord.Message) -> dict:
    return {
        "id": message.id,
        "channel_id": message.channel.id,
        "guild_id": message.guild.id if message.guild else None,
        "author": {
            "id": message.author.id,
            "name": str(message.author),
        },
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "attachments": [a.to_dict() for a in message.attachments],
        "embeds": [e.to_dict() for e in message.embeds],
    }


class BackfillClient(discord.Client):
    async def on_ready(self):
        logger.info("Connecté : %s (id=%s)", self.user, self.user.id)
        Base.metadata.create_all(bind=engine)

        channel_ids = settings.channel_id_list
        logger.info("Channel IDs depuis la config : %s", channel_ids)

        if not channel_ids:
            logger.warning("Aucun DISCORD_CHANNEL_IDS défini.")
            await self.close()
            return

        for channel_id in channel_ids:
            channel = self.get_channel(channel_id)
            if channel is None:
                logger.warning("Salon introuvable ou bot non présent: %s", channel_id)
                continue

            logger.info("Backfill salon %s (#%s)", channel_id, getattr(channel, "name", "?"))
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
                        raw_json=json.dumps(message_to_dict(message), default=str),
                    )
                    db.add(row)
                    db.commit()
                    inserted += 1

            logger.info("Salon %s terminé: %s messages insérés", channel_id, inserted)

        await self.close()


def main() -> None:
    token = settings.discord_bot_token
    if not token:
        raise RuntimeError("discord_bot_token non configuré dans .env (DISCORD_BOT_TOKEN)")

    logger.info("Démarrage du BackfillClient...")
    client = BackfillClient(intents=intents)
    client.run(token)


if __name__ == "__main__":
    main()