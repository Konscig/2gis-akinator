from environs import Env
from dataclasses import dataclass


@dataclass
class Bot:
    bot_token: str
    group_id: str
    admin_id: int


@dataclass
class Settings:
    bot: Bot


def get_settings(path: str):
    env = Env()
    env.read_env(path)

    return Settings(
        bot=Bot(
            bot_token=env.str("HTTP_API"),
            group_id=env.str("GROUP_ID"),
            admin_id=env.int("ADMIN_ID")
        )
    )


settings = get_settings('api')
print(settings)
