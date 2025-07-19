from aiogram.client.bot import Bot
from settings import settings


bot = Bot(settings.bot.bot_token, parse_mode='HTML')
