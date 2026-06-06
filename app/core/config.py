from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # For Railway deployment: Ensure you use the internal DATABASE_URL 
    # instead of DATABASE_PUBLIC_URL to avoid egress fees and use private networking.
    database_url: str = "postgresql://flights_user:flights_pass@db:5432/flights_db"
    
    google_cloud_api_key: str = ""
    scrape_interval_hours: int = 24
    timezone: str = "America/Los_Angeles"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
