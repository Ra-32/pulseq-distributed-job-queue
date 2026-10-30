from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./pulseq.db"
    redis_url: str = "redis://localhost:6379/0"
    api_key: str = "dev-secret-change-me"
    redis_stream: str = "pulseq:jobs"
    redis_group: str = "pulseq-workers"
    worker_name: str = "worker-local"
    poll_block_ms: int = 5000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
