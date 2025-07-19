from environs import Env
from dataclasses import dataclass


@dataclass
class Bot:
    bot_token: str
    group_id: str
    admin_id: int


@dataclass
class OpenAI:
    api_key: str
    model: str = "gpt-4o-mini"


@dataclass
class GIS:
    api_key: str


@dataclass
class Settings:
    bot: Bot
    openai: OpenAI
    gis: GIS


def get_settings(path: str):
    env = Env()
    env.read_env(path)

    return Settings(
        bot=Bot(
            bot_token=env.str("HTTP_API"),
            group_id=env.str("GROUP_ID"),
            admin_id=env.int("ADMIN_ID")
        ),
        openai=OpenAI(
            api_key=env.str("OPENAI_API_KEY"),
            model=env.str("OPENAI_MODEL", "gpt-4o-mini")
        ),
        gis=GIS(
            api_key=env.str("GIS_API_KEY", "")
        )
    )


settings = get_settings('api')
print(settings)
