from aiogram.dispatcher.dispatcher import Dispatcher
from aiogram.filters import CommandStart
from aiogram import types


dp = Dispatcher()


@dp.message(CommandStart())
async def command_start(message: types.Message) -> None:
    await message.answer(f"Здравствуйте, {message.from_user.full_name}")
