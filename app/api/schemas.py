from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    message_id: str
    guild_id: int
    channel_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime
    edited_at: datetime | None
    deleted: bool
    attachment_count: int
    embed_count: int


class PaginationOut(BaseModel):
    next_cursor: str | None
    limit: int


class MessageListOut(BaseModel):
    data: list[MessageOut]
    pagination: PaginationOut
