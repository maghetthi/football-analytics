from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class MlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str
    # Training only reads marts, so it uses the same SELECT-only role as the API.
    api_db_user: str = "api_reader"
    api_db_password: SecretStr

    artifacts_dir: str = "artifacts"
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
        )


@lru_cache
def get_settings() -> MlSettings:
    return MlSettings()
