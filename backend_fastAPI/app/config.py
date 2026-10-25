from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "ai_code_reviewer"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    gemini_api_key: str

    frontend_url: str = "http://localhost:5173"

    # Outgoing email (forgot-password codes).
    #   log   - print to the server log (local development)
    #   brevo - Brevo HTTPS API (works where SMTP ports are blocked, e.g. Render free)
    #   smtp  - any SMTP server (Gmail app password, Amazon SES SMTP on AWS, ...)
    # Empty disables email; forgot-password then answers 503.
    email_provider: str = ""
    email_from: str | None = None  # e.g. "KrishnaLens <no-reply@example.com>"

    brevo_api_key: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_ssl: bool = False    # True for port 465; otherwise STARTTLS is used

    project_version: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
