from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    postgres_user: str = "jobintel"
    postgres_password: str = "jobintel"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "jobintel"
    cors_origins: list[str] = ["http://localhost:3000"]
    kaggle_username: str = ""
    kaggle_key: str = ""

    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters (e.g. "@") in the password
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


settings = Settings()
