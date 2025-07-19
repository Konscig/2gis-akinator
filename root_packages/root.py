from aiogram.client.bot import Bot, DefaultBotProperties
from settings import settings


bot = Bot(settings.bot.bot_token, default=DefaultBotProperties(parse_mode='HTML'))
