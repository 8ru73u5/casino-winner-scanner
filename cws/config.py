import os
from enum import Enum
from typing import Any

from dotenv import find_dotenv, load_dotenv


class AppConfig:
    class Variables(Enum):
        SECRET_KEY = 'SECRET_KEY', str
        CASINO_ADMIN_USER = 'CASINO_ADMIN_USER', str
        CASINO_ADMIN_PASS = 'CASINO_ADMIN_PASS', str
        DATABASE_URL = 'CASINO_DATABASE_URL', str
        REDIS_HOST = 'REDIS_HOST', str
        REDIS_PORT = 'REDIS_PORT', int
        TELEGRAM_TOKEN = 'CWS_TELEGRAM_TOKEN', str
        TELEGRAM_CHAT_ID = 'CWS_TELEGRAM_CHAT_ID', str
        TELEGRAM_BET_BOT_CHAT_ID = 'CWS_TELEGRAM_BET_BOT_CHAT_ID', str
        WEBSHARE_API_TOKEN = 'WEBSHARE_API_TOKEN', str

    _vars = {}
    _loaded = False

    @classmethod
    def _load(cls):
        if not cls._loaded:
            load_dotenv(find_dotenv())

            for var in cls.Variables.__members__.values():
                name, var_type = var.value

                env = os.getenv(name)
                assert env is not None, f'Environment variable: {name} is not set!'

                if var_type is str:
                    pass
                elif var_type is int:
                    try:
                        env = int(env)
                    except ValueError:
                        raise ValueError(f'Environment variable: {name} should be an integer. Current value: {env}')
                elif var_type is bool:
                    env = env.lower()
                    if env not in ['true', 'false']:
                        raise ValueError(f'Environment variable {name} should be a boolean. Current value: {env}')
                    env = env == 'true'
                else:
                    raise NotImplementedError('Unsupported config type:', var_type)

                cls._vars[var] = env

            cls._loaded = True

    @classmethod
    def get(cls, var: Variables) -> Any:
        if not cls._loaded:
            cls._load()

        return cls._vars[var]
