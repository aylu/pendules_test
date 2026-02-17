from datetime import datetime

from dateutil.parser import isoparse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.api.schemas import MessageListOut, MessageOut, PaginationOut
from app.db.models import DiscordMessage
from app.db.session import get_db

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])


def _parse_datetime(name: str, value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return isoparse(value)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime for '{name}', expected ISO-8601",
        ) from exc


@router.get("/messages", response_model=MessageListOut)
def list_messages(
    guild_id: int,
    channel_id: int,
    from_ts: str | None = Query(default=None, alias="from"),
    to_ts: str | None = Query(default=None, alias="to"),
    cursor: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
):
    from_dt = _parse_datetime("from", from_ts)
    to_dt = _parse_datetime("to", to_ts)

    stmt: Select[tuple[DiscordMessage]] = (
        select(DiscordMessage)
        .where(DiscordMessage.guild_id == guild_id)
        .where(DiscordMessage.channel_id == channel_id)
        .order_by(DiscordMessage.created_at.asc(), DiscordMessage.message_id.asc())
    )

    if from_dt:
        stmt = stmt.where(DiscordMessage.created_at >= from_dt)
    if to_dt:
        stmt = stmt.where(DiscordMessage.created_at <= to_dt)
    if not include_deleted:
        stmt = stmt.where(DiscordMessage.deleted.is_(False))
    if cursor:
        stmt = stmt.where(DiscordMessage.message_id > cursor)

    rows = db.execute(stmt.limit(limit + 1)).scalars().all()
    has_next = len(rows) > limit
    data_rows = rows[:limit]

    next_cursor = data_rows[-1].message_id if has_next and data_rows else None

    return MessageListOut(
        data=[
            MessageOut(
                message_id=m.message_id,
                guild_id=m.guild_id,
                channel_id=m.channel_id,
                author_id=m.author_id,
                author_name=m.author_name,
                content=m.content,
                created_at=m.created_at,
                edited_at=m.edited_at,
                deleted=m.deleted,
                attachment_count=m.attachment_count,
                embed_count=m.embed_count,
            )
            for m in data_rows
        ],
        pagination=PaginationOut(next_cursor=next_cursor, limit=limit),
    )


@router.get("/messages/{message_id}", response_model=MessageOut)
def get_message(message_id: str, db: Session = Depends(get_db)):
    message = db.get(DiscordMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageOut(
        message_id=message.message_id,
        guild_id=message.guild_id,
        channel_id=message.channel_id,
        author_id=message.author_id,
        author_name=message.author_name,
        content=message.content,
        created_at=message.created_at,
        edited_at=message.edited_at,
        deleted=message.deleted,
        attachment_count=message.attachment_count,
        embed_count=message.embed_count,
    )
