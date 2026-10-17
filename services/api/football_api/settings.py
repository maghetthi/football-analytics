from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class ApiSettings(BaseSettings):
    # .env is read from the current directory; run from the repo root (make api does).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # Managed databases (Neon, Supabase) require TLS: set POSTGRES_SSLMODE=require there.
    postgres_sslmode: str | None = None
    postgres_db: str

    # The API never uses the owner account: it connects as a SELECT-only role on `marts`.
    api_db_user: str = "api_reader"
    api_db_password: SecretStr

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600

    # Directory holding the trained model bundle written by `make train`.
    artifacts_dir: str = "models"

    # Comma-separated. Empty means every request is rejected (secure by default).
    api_keys: SecretStr = SecretStr("")

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.api_db_user,
            password=self.api_db_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode} if self.postgres_sslmode else {},
        )

    @property
    def valid_api_keys(self) -> tuple[str, ...]:
        return tuple(k.strip() for k in self.api_keys.get_secret_value().split(",") if k.strip())


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()
