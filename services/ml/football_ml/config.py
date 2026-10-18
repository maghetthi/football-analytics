from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class MlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # Managed databases (Neon, Supabase) require TLS: set POSTGRES_SSLMODE=require there.
    postgres_sslmode: str | None = None
    postgres_db: str
    # Training only reads marts, so it uses the same SELECT-only role as the API.
    api_db_user: str = "api_reader"
    api_db_password: SecretStr

    # Only needed by jobs that WRITE predictions (the owner account); reading works with api_reader.
    postgres_user: str | None = None
    postgres_password: SecretStr | None = None

    artifacts_dir: str = "models"
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"

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
    def write_url(self) -> URL:
        if self.postgres_user is None or self.postgres_password is None:
            raise RuntimeError(
                "POSTGRES_USER and POSTGRES_PASSWORD are required to write predictions"
            )
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"sslmode": self.postgres_sslmode} if self.postgres_sslmode else {},
        )


@lru_cache
def get_settings() -> MlSettings:
    return MlSettings()
