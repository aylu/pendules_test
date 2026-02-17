from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "discord-reporting-api"
    api_key: str = "change-me"
    database_url: str = "sqlite:///./discord_messages.db"
    discord_bot_token: str = ""
    discord_guild_id: int | None = None
    discord_channel_ids: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def channel_id_list(self) -> list[int]:
        if not self.discord_channel_ids.strip():
            return []
        return [int(x.strip()) for x in self.discord_channel_ids.split(",") if x.strip()]


settings = Settings()
