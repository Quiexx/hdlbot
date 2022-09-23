import json
import re
import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Filter
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ContentType

import crud
import models
from BotLogger import BotLogger
from database import engine, SessionLocal

# TODO move token to env
# TOKEN = os.getenv('TELEGRAM_TOKEN')

models.Base.metadata.create_all(bind=engine)
logging.basicConfig(level=logging.INFO)

# db = SessionLocal()
# db.close()


with open("config.json", "r") as f:
    config = json.load(f)

storage = MemoryStorage()
bot = Bot(config["API_key"])
dp = Dispatcher(bot, storage=storage)
logger = BotLogger(bot, config["log_chat_id"])

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
VALID_SYMS_REGEX = re.compile(r'^[A-Za-z.!@?#\"$%&:;()\\\/ 0-9-]*$')


class ValidSymbols(Filter):
    key = "is_valid_symbols"

    async def check(self, message: types.Message):
        return VALID_SYMS_REGEX.fullmatch(message.text)


class RegisterUserStates(StatesGroup):
    add_email = State()


def extract_unique_code(text):
    # Extracts the unique_code from the start command.
    return text.split()[1] if len(text.split()) > 1 else None


@dp.message_handler(ValidSymbols(), commands=['start'], content_types=[ContentType.TEXT])
# @logger.log_handler
async def handle_start_message(message: Message, state: FSMContext, *args, **kwargs):
    task_code = extract_unique_code(message.text)

    # await logger.log(task_code)
    async with state.proxy() as data:
        if task_code:
            data["question"] = task_code

    db = SessionLocal()
    users = crud.get_user_by_chat(db, str(message.chat.id))

    if not users:
        reply = "Введите ваш email"
        await RegisterUserStates.add_email.set()
        await message.answer(reply)
        db.close()
        return

    if not task_code:
        reply = "Ищи QR коды, дубина"
        async with state.proxy() as data:
            data.clear()
        markup = None
        await message.answer(reply, reply_markup=markup)
        db.close()
        return

    question = crud.get_question(db, task_code)

    if not question:
        reply = "Ищи QR коды, дубина"
        markup = None
        async with state.proxy() as data:
            data.clear()
        await message.answer(reply, reply_markup=markup)
        db.close()
        return

    user_question = crud.get_user_question_by_u_q(db, users.id, question.id)
    if user_question:
        reply = "Хитрюга, ты уже отвечал на этот вопрос :)"
        # await logger.log(f"user: {users.id}\tquestion: {question.id}\tuser_question: {user_question.users_id}, {user_question.question_id}")
        markup = None
        async with state.proxy() as data:
            data.clear()
        await message.answer(reply, reply_markup=markup)
        db.close()
        return

    reply = question.text
    buttons = [InlineKeyboardButton(answ, callback_data="cb_" + answ) for answ in list(question.answers)]
    conf_button = InlineKeyboardButton("Отправить ответ", callback_data="cb_confirm")
    markup = InlineKeyboardMarkup()
    markup.add(*buttons)
    markup.add(conf_button)

    if question.photo:
        await bot.send_photo(
            message.chat.id,
            question.photo,
            caption=reply,
            reply_markup=markup
        )
        db.close()
        return

    db.close()
    await message.answer(reply, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data.startswith("cb_"))
# @logger.log_handler
async def callback_answer_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    if call.data == "cb_confirm":
        async with state.proxy() as data:
            q_id = data.get("question")
            answers = data.get("current_answers")
            data.clear()

        db = SessionLocal()
        question = crud.get_question(db, q_id)
        user = crud.get_user_by_chat(db, call.message.chat.id)
        category = crud.get_category(db, question.category_id)
        print(user)
        print(category)
        print(question.category_id)
        score = crud.get_user_score(db, user.id, category.id)
        if not score:
            score = crud.create_user_score(db, user.id, category.id)

        score_delta = 0
        reply = "Неверно"
        if answers and set(question.cor_answers) == set(answers):
            reply = "Верно"
            score_delta = question.score
            crud.update_user_score(db, user.id, category.id, score.score + score_delta)

        crud.create_user_question(db, user.id, user.chat_id, question.id, answers, score_delta)

        scores = crud.get_user_scores(db, user.id)
        categoties = [crud.get_category(db, cat.category_id) for cat in scores]

        db.close()
        reply += "\nВаши счета"
        reply += ''.join([f"\n{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores)])

        disable_buttons(call)
        await call.message.edit_reply_markup(reply_markup=call.message.reply_markup)
        await call.message.answer(reply)
        return

    elif call.data != "disabled":
        check_buttons(call)
        async with state.proxy() as data:
            data["current_answers"] = []
            for row in call.message.reply_markup.inline_keyboard:
                for b in row:
                    if b.text.startswith(config["check_icon"]):
                        data["current_answers"].append(b.text[2:])

        await call.message.edit_reply_markup(reply_markup=call.message.reply_markup)
        await call.answer()
        return


def check_buttons(call: CallbackQuery):
    def check_button(b):
        if b.callback_data == call.data:
            if b.text.startswith(config["check_icon"]):
                b.text = b.text[2:]
            else:
                b.text = config["check_icon"] + b.text
        return b

    keyboard = call.message.reply_markup.inline_keyboard
    for row in keyboard:
        for button in row:
            check_button(button)


def disable_buttons(call: CallbackQuery):
    def disable_button(b):
        b.callback_data = 'disabled'
        return b

    keyboard = call.message.reply_markup.inline_keyboard
    for row in keyboard:
        for button in row:
            disable_button(button)


@dp.message_handler(state=RegisterUserStates.add_email)
# @logger.log_handler
async def register_user(message: Message, state: FSMContext, *args, **kwargs):
    email = message.text

    if not EMAIL_REGEX.fullmatch(email):
        reply = "Не похоже не email :/. Попробуйте еще раз"
        await message.answer(reply)
        return

    db = SessionLocal()
    crud.create_user(db, chat_id=message.chat.id, email=email)
    db.close()
    async with state.proxy() as data:
        if data.get("question"):
            message.text = f"/start {data['question']}"
        else:
            message.text = "/start"
    await state.finish()
    await handle_start_message(message, state, *args, **kwargs)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
