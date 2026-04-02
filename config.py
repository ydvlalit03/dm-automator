import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-to-a-random-32-char-string"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "changeme123"

    # Instagram / Meta
    WEBHOOK_VERIFY_TOKEN: str = "my-random-verify-token"
    META_APP_SECRET: str = ""
    IG_PAGE_ACCESS_TOKEN: str = ""
    IG_BUSINESS_ACCOUNT_ID: str = ""

    # LinkedIn
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""

    # Rate Limits
    DM_RATE_LIMIT_PER_DAY: int = 200

    DATABASE_URL: str = "sqlite:///./dm_automator.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_secret_key(self) -> str:
        """Auto-generate a secret key if the default is still in use."""
        if self.SECRET_KEY == "change-me-to-a-random-32-char-string":
            return secrets.token_hex(32)
        return self.SECRET_KEY


settings = Settings()
