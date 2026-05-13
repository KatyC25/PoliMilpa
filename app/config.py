import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Polimilpa API"
    app_version: str = "0.1.0"
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")


settings = Settings()
