from config.components.auth import AuthConfig
from config.components.base import BaseConfig
from config.components.db import DatabaseConfig
from config.components.redis import RedisConfig


class ComponentsConfig(BaseConfig, DatabaseConfig, RedisConfig, AuthConfig):
    pass


__all__ = ["ComponentsConfig"]