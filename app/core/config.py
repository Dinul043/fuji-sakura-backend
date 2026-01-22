"""
Configuration settings for the application
Loads environment variables and provides app settings
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App Configuration
    APP_NAME: str = "Fuji Sakura Food Delivery"
    DEBUG: bool = True
    
    # Database Configuration
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/fuji_sakura_db"
    
    # JWT Configuration
    SECRET_KEY: str = "fuji-sakura-super-secret-key-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    
    # Email Configuration (Mailtrap)
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: str = "noreply@fujisakura.com"
    MAIL_SERVER: str = "sandbox.smtp.mailtrap.io"
    MAIL_PORT: int = 2525
    
    # OTP Configuration
    OTP_EXPIRE_MINUTES: int = 10
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()