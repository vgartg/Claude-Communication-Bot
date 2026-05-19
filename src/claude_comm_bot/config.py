from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(..., description="Telegram bot token from @BotFather.")
    host: str = "127.0.0.1"
    port: int = 3000
    data_dir: Path = Field(
        Path("./data"),
        description="Directory for persistent state (user registry, etc.).",
    )
    ask_timeout: int = Field(
        60,
        description="Default seconds to wait on /api/ask. Hook scripts fall back to terminal "
        "when the bot times out. 0 = wait forever.",
    )
    admin_user_ids: list[int] = Field(
        default_factory=list,
        description="Optional allowlist of Telegram user IDs that may use admin commands "
        "(/users, /broadcast). Comma-separated in env: CCB_ADMIN_USER_IDS=123,456.",
    )

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def _split_admin_ids(cls, v: object) -> object:
        # Accept "" → [], "123" → [123], "123,456" → [123,456], list passes through.
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    model_config = SettingsConfigDict(
        env_prefix="CCB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
