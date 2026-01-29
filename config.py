"""
Application Configuration
Centralized configuration management for The Manager app.
"""
import os
from typing import Optional


class Config:
    """Application configuration with environment variable support."""

    # === Database & API ===
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # === Timeouts (seconds) ===
    AI_TIMEOUT: int = int(os.getenv("AI_TIMEOUT", "45"))
    DB_TIMEOUT: int = int(os.getenv("DB_TIMEOUT", "20"))
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "300"))
    REALTIME_POLL_INTERVAL: int = 2

    # === File Upload Limits ===
    MAX_FILE_SIZE_MB: int = 50
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    SIGNED_URL_EXPIRY_SECONDS: int = 60 * 60 * 24 * 365  # 1 year

    # === Pagination & Limits ===
    DEFAULT_MESSAGE_LIMIT: int = 50
    MAX_MESSAGE_LIMIT: int = 100
    MAX_SEARCH_RESULTS: int = 30
    UNREAD_COUNT_CAP: int = 99
    MAX_TOPICS_PER_CHANNEL: int = 500

    # === Cache TTL (seconds) ===
    CATEGORY_CACHE_TTL: int = 300  # 5 minutes
    ROLE_CACHE_TTL: int = 600  # 10 minutes

    # === UI Colors ===
    class Colors:
        PRIMARY = "#2E7D32"
        PRIMARY_LIGHT = "#E3F2FD"
        SECONDARY = "#1565C0"
        ERROR = "#FF5252"
        WARNING = "#FF9800"
        SUCCESS = "#4CAF50"
        TEXT_PRIMARY = "#212121"
        TEXT_SECONDARY = "#757575"
        BACKGROUND = "#FFFFFF"
        SURFACE = "#FAFAFA"
        BORDER = "#E0E0E0"

    # === Subscription Tiers ===
    class Tiers:
        FREE = "free"
        STANDARD = "standard"
        PREMIUM = "premium"

        # Audio retention days by tier
        AUDIO_RETENTION = {
            "free": 3,
            "standard": 30,
            "premium": 365
        }

        # Text retention days by tier (None = unlimited)
        TEXT_RETENTION = {
            "free": 30,
            "standard": None,
            "premium": None
        }

    # === Payroll ===
    DEFAULT_HOURLY_WAGE: int = 9860  # 2024 Korea minimum wage
    MAX_HOURLY_WAGE: int = 100000

    # === Routes ===
    class Routes:
        LOGIN = "login"
        SIGNUP = "signup"
        HOME = "home"
        CHAT = "chat"
        CALENDAR = "calendar"
        VOICE = "voice"
        CLOSING = "closing"
        WORK = "work"
        PROFILE = "profile"
        STORE_MANAGE = "store_manage"
        ONBOARDING = "onboarding"

    # === Roles ===
    class Roles:
        OWNER = "owner"
        MANAGER = "manager"
        STAFF = "staff"

        # Roles that can modify member permissions
        ADMIN_ROLES = ["owner", "manager"]

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        errors = []
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is required")
        if not cls.SUPABASE_KEY:
            errors.append("SUPABASE_KEY is required")

        if errors:
            for err in errors:
                print(f"CONFIG ERROR: {err}")
            return False
        return True


# Singleton instance
config = Config()
