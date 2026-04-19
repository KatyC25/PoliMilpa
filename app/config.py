from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Polimilpa API"
    app_version: str = "0.1.0"


settings = Settings()
