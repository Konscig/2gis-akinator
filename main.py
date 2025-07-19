import sys
import asyncio
import logging

from root_packages.root import bot
from root_packages.handlers.standart_handler import dp


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
