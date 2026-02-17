from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.base import Base
from app.db.models import DiscordMessage
from app.db.session import SessionLocal, engine
from app.main import app


def setup_module():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.query(DiscordMessage).delete()
        db.add(
            DiscordMessage(
                message_id="1",
                guild_id=10,
                channel_id=20,
                author_id=30,
                author_name="alice",
                content="hello",
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
                edited_at=None,
                deleted=False,
                attachment_count=0,
                embed_count=0,
                raw_json="{}",
            )
        )
        db.commit()


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_messages_requires_api_key():
    client = TestClient(app)
    response = client.get("/v1/messages", params={"guild_id": 10, "channel_id": 20})
    assert response.status_code == 401


def test_messages_with_api_key():
    client = TestClient(app)
    response = client.get(
        "/v1/messages",
        params={"guild_id": 10, "channel_id": 20},
        headers={"x-api-key": settings.api_key},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["message_id"] == "1"
