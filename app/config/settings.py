from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

import os

class Settings(BaseSettings):
    ENV: str = os.getenv("ENV", "dev")
    
    # API Config
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Logistics AI Agent"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis / Celery
    REDIS_URL: str

    # External APIs (ALL OPTIONAL for local free mode)
    OPENAI_API_KEY: Optional[str] = ""
    GOOGLE_MAPS_API_KEY: Optional[str] = ""
    STRIPE_SECRET_KEY: Optional[str] = ""

    # WhatsApp API (optional for local mode)
    WEBHOOK_VERIFY_TOKEN: Optional[str] = "local-dev-token"
    WHATSAPP_TOKEN: Optional[str] = ""
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = ""

    # Twilio Sandbox
    TWILIO_ACCOUNT_SID: Optional[str] = ""
    TWILIO_AUTH_TOKEN: Optional[str] = ""
    TWILIO_WHATSAPP_NUMBER: Optional[str] = "whatsapp:+14155238886"

    # Monitoring (optional)
    SENTRY_DSN: Optional[str] = ""

    # Real-World Simulation
    SIMULATE_DELAY: bool = False
    SIMULATE_FAILURE_RATE: float = 0.0

    # Conversational AI settings (Ollama / HuggingFace proxy support)
    AI_PROVIDER: str = "disabled"  # disabled | ollama | huggingface
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    HUGGINGFACE_API_KEY: Optional[str] = None
    HUGGINGFACE_MODEL: str = "mistralai/Mistral-7B-Instruct-v0.2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
