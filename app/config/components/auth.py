from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.constants import ENV_FILE_PATH


class AuthConfig(BaseSettings):
    yandex_client_id: str
    yandex_client_secret: str
    secret_key: str
    redirect_uri: str
    yandex_oauth_url: str
    yandex_token_url: str
    yandex_api_base_url: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding='utf-8',
    )
