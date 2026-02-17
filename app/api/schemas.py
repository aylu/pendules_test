from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    message_id: str
    author_name: str
    content: str
    created_at: datetime
    edited_at: datetime | None

class MessageListOut(BaseModel):
    data: list[MessageOut]
