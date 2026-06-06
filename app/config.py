from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://flights_user:flights_pass@db:5432/flights_db"
    google_cloud_api_key: str = ""
    scrape_interval_hours: int = 24
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
