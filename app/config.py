import os

from pydantic import BaseModel


def _parse_extra_origins(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseModel):
    app_name: str = "Polimilpa API"
    app_version: str = "0.1.0"
    frontend_url: str = os.getenv("FRONTEND_URL", "https://poli-milpa-h5sp.vercel.app")
    extra_origins: list[str] = _parse_extra_origins(os.getenv("EXTRA_CORS_ORIGINS"))


settings = Settings()
