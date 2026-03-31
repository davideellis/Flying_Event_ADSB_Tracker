from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FEAT_")

    app_name: str = "Flying Event ADS-B Tracker"
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./flying_event_adsb_tracker.db"
    password_reset_base_url: str = "http://localhost:8000"
    session_cookie_name: str = "feat_session"
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "ChangeMe123!"

    adsb_provider: str = "stub"
    adsb_poll_seconds: int = 10
    adsb_http_base_url: str = "https://api.adsb.lol"
    adsb_http_area_path_template: str = "/v2/lat/{lat}/lon/{lon}/dist/{dist}"
    adsb_http_timeout_seconds: float = 10.0
    adsb_worker_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
