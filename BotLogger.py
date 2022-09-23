from typing import Callable

import ujson
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery


class BotLogger:
    def __init__(self, bot, log_chat_id: int):
        self.__bot = bot
        self.__log_chat_id = log_chat_id

    def log_handler(self, handler: Callable) -> Callable:
        async def decorator(message: Message, state: FSMContext, *args, **kwargs):
            json_mes = ujson.dumps(dict(message), indent=4, ensure_ascii=False)

            str_state = await state.get_state()

            await self.log(f"State: {str_state}\nHandler: {handler.__name__}\n" + json_mes)
            try:
                await handler(message, state, *args, **kwargs)
            except Exception as exc:
                await self.log(
                    f"Got exception\n\n{exc.__class__.__name__}: {exc}\nState: {str_state}\nHandler: {handler.__name__}"
                )

        return decorator

    async def log(self, message):
        await self.__bot.send_message(self.__log_chat_id, message)
