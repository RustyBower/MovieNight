from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "change-me"
    plex_app_client_id: str = "movienight-web-app"
    plex_app_name: str = "Movie Night"
    base_url: str = ""  # auto-detected from request if blank

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
