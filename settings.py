from os import getenv
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

@dataclass
class Bot:
    bot_token: str


@dataclass
class OpenAI:
    api_key: str
    model: str = "gpt-4.1-mini"


@dataclass
class GIS:
    api_key: str


@dataclass
class Settings:
    bot: Bot
    openai: OpenAI
    gis: GIS


def get_settings(path: str):
    return Settings(
        bot=Bot(
            bot_token=getenv("TELEGRAM_BOT_TOKEN"),
        ),
        openai=OpenAI(
            api_key=getenv("OPENAI_API_KEY"),
            model=getenv("OPENAI_MODEL", "gpt-4.1-mini")
        ),
        gis=GIS(
            api_key=getenv("GIS_API_KEY", "")
        )
    )


settings = get_settings('api')
print(settings)
