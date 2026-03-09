from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Zeron CRM API"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://zeron_user:zeron_password@localhost:5432/zeron_crm"
    SECRET_KEY: str = "ET5aLUQreKBGJNiPfJf8QO76UGNw3_gNa1zfGoxVIW3WT1za64D0eMdYWuelOSjM"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = ""  # 64 hex chars = 32 bytes for AES-256-GCM
    BACKUP_DIR: str = "/home/ubuntu/backups/zeron-crm"

    class Config:
        env_file = ".env"

settings = Settings()
