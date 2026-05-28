from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TPS MAAQ"
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"
    demo_email: str = "admin@maaq.pe"
    demo_password: str = "demo123"

    database_url: Optional[str] = Field(default=None)
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_server: str = "localhost"
    db_port: Optional[int] = None
    db_name: str = "maaq_bd"
    db_user: Optional[str] = "sa"
    db_password: Optional[str] = None
    db_trusted_connection: bool = False
    db_encrypt: bool = False
    db_trust_server_certificate: bool = True
    db_connection_timeout: int = 5

    @property
    def sqlalchemy_url(self):
        if self.database_url:
            return self.database_url

        query = {
            "driver": self.db_driver,
            "Encrypt": "yes" if self.db_encrypt else "no",
            "TrustServerCertificate": "yes" if self.db_trust_server_certificate else "no",
            "Connection Timeout": str(self.db_connection_timeout),
        }

        username = self.db_user
        password = self.db_password

        if self.db_trusted_connection:
            query["Trusted_Connection"] = "yes"
            username = None
            password = None

        return URL.create(
            "mssql+pyodbc",
            username=username,
            password=password,
            host=self.db_server,
            port=self.db_port,
            database=self.db_name,
            query=query,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
