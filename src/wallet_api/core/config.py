from decimal import Decimal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    RABBIT_HOST: str
    RABBIT_USER: str
    RABBIT_PASS: SecretStr
    RABBIT_PORT: int

    @property
    def rabbit_url(self):
        return f"amqp://{self.RABBIT_USER}:{self.RABBIT_PASS.get_secret_value()}@{self.RABBIT_HOST}:{self.RABBIT_PORT}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    @property
    def redis_url(self):
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis: RedisSettings = RedisSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()

    DB_HOST: str
    DB_USER: str
    DB_PASS: SecretStr
    DB_PORT: int
    DB_NAME: str
    SECRET_KEY: str
    MAX_ACCESS_AGE: int
    MAX_REFRESH_AGE: int
    MAX_SINGLE_DEPOSIT: Decimal
    MAX_DAILY_DEPOSIT: Decimal
    MAX_TRANSFER_AMOUNT: Decimal
    PENDING_TTL: int
    COMPLETED_TTL: int
    EXCHANGE_LIMIT_RUB: Decimal
    EXCHANGE_LIMIT_USD_EUR: Decimal

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def db_url_sync(self):
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
