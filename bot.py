import json
import re
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Filter
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ContentType, \
    ReplyKeyboardMarkup, KeyboardButton, BotCommand, ReplyKeyboardRemove, MenuButtonCommands, MenuButtonDefault, \
    MessageEntity

import crud
import models
from database import engine, SessionLocal

# TODO move token to env
# TOKEN = os.getenv('TELEGRAM_TOKEN')

models.Base.metadata.create_all(bind=engine)
logging.basicConfig(level=logging.INFO)

# db = SessionLocal()
# db.close()


with open("config.json", "r") as f:
    config = json.load(f)

messages = config["messages"]
storage = MemoryStorage()
bot = Bot(config["API_key"])
dp = Dispatcher(bot, storage=storage)

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
VALID_SYMS_REGEX = re.compile(r'^[A-Za-z.!@?#\"$%&:;()\\\/ 0-9-]*$')


class ValidSymbols(Filter):
    key = "is_valid_symbols"

    async def check(self, message: types.Message):
        return VALID_SYMS_REGEX.fullmatch(message.text)


class RegisterUserStates(StatesGroup):
    add_email = State()


async def extract_unique_code(text):
    # Extracts the unique_code from the start command.
    return text.split()[1] if len(text.split()) > 1 else None


async def message_to_log(message: Message):
    # dt_object = datetime.fromtimestamp(timestamp)
    d_mes = dict(message)
    try:
        try:
            log = "{} - message from {} {} {} - text: {}".format(
                datetime.fromtimestamp(d_mes["date"]),
                d_mes["chat"]["first_name"],
                d_mes["chat"]["last_name"],
                d_mes["chat"]["username"],
                d_mes["text"],
            )
        except Exception as exc:
            log = "{} - message in chat {} - text: {}".format(
                datetime.fromtimestamp(d_mes["date"]),
                d_mes["chat"]["id"],
                d_mes["text"]
            )
    except Exception as exc:
        log = str(exc)
    return log


async def call_to_log(call: CallbackQuery):
    # dt_object = datetime.fromtimestamp(timestamp)
    d_mes = dict(call)
    try:
        try:
            log = "{} - callback from {} {} {} - data: {}".format(
                datetime.fromtimestamp(d_mes["message"]["date"]),
                d_mes["message"]["chat"]["first_name"],
                d_mes["message"]["chat"]["last_name"],
                d_mes["message"]["chat"]["username"],
                d_mes["data"],
            )
        except Exception as exc:
            log = "{} - callback in chat {} - text: {}".format(
                datetime.fromtimestamp(d_mes["message"]["date"]),
                d_mes["message"]["chat"]["id"],
                d_mes["data"]
            )
    except Exception as exc:
        log = str(exc)
    return log

# @dp.message_handler()
# async def handle_any_message(message: Message, state: FSMContext, *args, **kwargs):
#     await message.answer(message.chat.id)

@dp.message_handler(ValidSymbols(), commands=['start'], content_types=[ContentType.TEXT])
async def handle_start_message(message: Message, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await message_to_log(message))
    task_code = await extract_unique_code(message.text)

    async with state.proxy() as data:
        if task_code:
            data["question"] = task_code

    db = SessionLocal()
    users = crud.get_user_by_chat(db, str(message.chat.id))

    if not users:
        reply = messages["input_email"]
        await RegisterUserStates.add_email.set()
        await message.answer(reply, reply_markup=ReplyKeyboardRemove())
        db.close()
        return

    if not task_code:
        reply = messages["find_QR"]
        async with state.proxy() as data:
            data.clear()
        markup = None
        await message.answer(reply, reply_markup=markup)
        db.close()
        return

    question = crud.get_question(db, task_code)

    if not question:
        reply = messages["find_QR"]
        markup = None
        async with state.proxy() as data:
            data.clear()
        await message.answer(reply, reply_markup=markup)
        db.close()
        return

    user_question = crud.get_user_question_by_u_q(db, users.id, question.id)
    if user_question:
        reply = messages["already_answered"]
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
async def callback_answer_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await call_to_log(call))
    if call.data == "cb_confirm":
        async with state.proxy() as data:
            q_id = data.get("question")
            answers = data.get("current_answers")
            data.clear()

        db = SessionLocal()
        question = crud.get_question(db, q_id)
        user = crud.get_user_by_chat(db, call.message.chat.id)
        category = crud.get_category(db, question.category_id)
        score = crud.get_user_score(db, user.id, category.id)
        if not score:
            score = crud.create_user_score(db, user.id, category.id)
            # scores = crud.get_user_scores(db, user.id)
            # if any([not sc.active for sc in scores]):
            #     crud.update_user_score_active(db, user.id, category.id, False)
            reqs = crud.get_shop_requests_by_chat(db, user.chat_id)
            if any([req.status == "ACCEPTED" for req in reqs]):
                crud.update_user_score_active(db, user.id, category.id, False)

        score_delta = 0
        reply = messages["incorrect_answer"]
        if answers and set(question.cor_answers) == set(answers):
            reply = messages["correct_answer"]
            score_delta = question.score
            crud.update_user_score(db, user.id, category.id, score.score + score_delta)

        crud.create_user_question(db, user.id, user.chat_id, question.id, answers, score_delta)

        scores = crud.get_user_scores(db, user.id)
        categoties = [crud.get_category(db, cat.category_id) for cat in scores]

        db.close()
        reply_scores = "\n" + messages["scores"]
        active_scores = ''.join([f"\n •{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if sc.active])
        inactive_scores = ''.join(
            [f"\n •{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if not sc.active])
        reply += reply_scores.format(active_scores, inactive_scores)

        await disable_buttons(call)
        await call.message.edit_reply_markup(reply_markup=call.message.reply_markup)
        await call.message.answer(reply)
        return

    elif call.data != "disabled":
        await check_buttons(call)
        async with state.proxy() as data:
            data["current_answers"] = []
            for row in call.message.reply_markup.inline_keyboard:
                for b in row:
                    if b.text.startswith(config["check_icon"]):
                        data["current_answers"].append(b.text[2:])

        await call.message.edit_reply_markup(reply_markup=call.message.reply_markup)
        await call.answer()
        return


async def check_buttons(call: CallbackQuery):
    async def check_button(b):
        if b.callback_data == call.data:
            if b.text.startswith(config["check_icon"]):
                b.text = b.text[2:]
            else:
                b.text = config["check_icon"] + b.text
        return b

    keyboard = call.message.reply_markup.inline_keyboard
    for row in keyboard:
        for button in row:
            await check_button(button)


async def disable_buttons(call: CallbackQuery):
    async def disable_button(b):
        b.callback_data = 'disabled'
        return b

    keyboard = call.message.reply_markup.inline_keyboard
    for row in keyboard:
        for button in row:
            await disable_button(button)


@dp.message_handler(state=RegisterUserStates.add_email)
async def register_user(message: Message, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await message_to_log(message))
    email = message.text

    if email.startswith("/"):
        reply = messages["need_register"]
        await message.answer(reply)
        return

    if not EMAIL_REGEX.fullmatch(email):
        reply = messages["incorrect_email"]
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

    await message.answer(messages["instructions"])
    await state.finish()
    await handle_start_message(message, state, *args, **kwargs)


@dp.callback_query_handler(lambda call: call.data.startswith("disabled"))
async def callback_disabled_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await call_to_log(call))
    await call.answer(messages["already_answered"])


@dp.message_handler(ValidSymbols(), commands=['scores'], content_types=[ContentType.TEXT])
async def handle_scores_command(message: Message, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await message_to_log(message))
    db = SessionLocal()
    user = crud.get_user_by_chat(db, message.chat.id)
    scores = crud.get_user_scores(db, user.id)

    if scores:
        categoties = [crud.get_category(db, cat.category_id) for cat in scores]
        reply_scores = "\n" + messages["scores"]
        active_scores = ''.join([f"\n\t\t{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if sc.active])
        inactive_scores = ''.join(
            [f"\n\t\t{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if not sc.active])
        reply = reply_scores.format(active_scores, inactive_scores)
    else:
        reply = "Вы еще не ответили ни на один вопрос"

    db.close()
    await message.answer(reply)


@dp.message_handler(ValidSymbols(), commands=['shop'], content_types=[ContentType.TEXT])
async def handle_shop_command(message: Message, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await message_to_log(message))
    db = SessionLocal()
    merch = crud.get_all_merch(db)
    user = crud.get_user_by_chat(db, message.chat.id)
    scores = crud.get_user_scores(db, user.id)

    if scores:
        categoties = [crud.get_category(db, cat.category_id) for cat in scores]
        scores_mes = "\n" + messages["scores"]
        active_scores = ''.join([f"\n •{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if sc.active])
        inactive_scores = ''.join(
            [f"\n •{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if not sc.active])
        scores_mes = scores_mes.format(active_scores, inactive_scores)
    else:
        scores_mes = "У вас пока нет баллов"

    shop_requests = crud.get_shop_requests_by_status(db, message.chat.id, "WAITING")
    db.close()

    reply = messages["shop_rules"]
    reply += "".join([f"\n •{m.name}: цена - {m.cost} баллов, осталось {m.count} шт" for m in merch])
    reply += "\n" + scores_mes
    markup = InlineKeyboardMarkup()

    no_shop_reqs = len(shop_requests) == 0

    if scores and no_shop_reqs:
        button = InlineKeyboardButton("Оставить заявку", callback_data="shop_req")
        markup.add(button)

    if not no_shop_reqs:
        reply += f"\nУ тебя уже есть активная заявка. Ее номер: {shop_requests[-1].id}"

    await message.answer(reply, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data.startswith("shop_req"))
async def callback_shopreq_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    logging.log(logging.INFO, await call_to_log(call))
    db = SessionLocal()
    shop_requests = crud.get_shop_requests_by_status(db, call.message.chat.id, "WAITING")
    if shop_requests:
        db.close()
        await call.message.answer(f"\nУ тебя уже есть активная заявка. Ее номер: {shop_requests[-1].id}")
        await call.answer()
        return

    shop_request = crud.create_shop_request(db, call.message.chat.id, status="WAITING")
    db.close()
    reply = f"Код вашей заявки: {shop_request.id}\nПокажите этот код на стенде, чтобы обменять ваши баллы на призы"
    await call.message.answer(reply)
    await call.answer()
    db = SessionLocal()
    user = crud.get_user_by_chat(db, call.message.chat.id)
    scores = crud.get_user_scores(db, user.id)
    merch = crud.get_all_merch(db)

    if scores:
        categoties = [crud.get_category(db, cat.category_id) for cat in scores]
        scores_mes = "\n" + messages["scores"]
        active_scores = ''.join([f"\n •{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if sc.active])
        inactive_scores = ''.join(
            [f"\n •{cat.name} - {sc.score}" for cat, sc in zip(categoties, scores) if not sc.active])
        scores_mes = scores_mes.format(active_scores, inactive_scores)
    else:
        scores_mes = "У пользователя нет баллов"
    db.close()

    merch_buttons = [[InlineKeyboardButton(f"{m.name}-{m.cost}-{m.count}шт",
                                           callback_data=f"req_add_merch_{m.id}_{shop_request.id}")] for m in merch if
                     m.count != 0]

    buttons = [
        *merch_buttons,
        [InlineKeyboardButton("Отклонить", callback_data=f"req_reject_{shop_request.id}")]
    ]
    reply_shop = f"Заявка: {shop_request.id}\nОт: {user.email}\n{scores_mes}"
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(config["shop_requests_chat_id"], reply_shop, reply_markup=markup, )


@dp.callback_query_handler(lambda call: call.data.startswith("req_reject_"))
async def callback_reject_req_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    req_id = int(call.data[len("req_reject_"):])
    db = SessionLocal()
    crud.update_shop_request_status(db, req_id, status="REJECTED")
    db.close()
    await call.message.delete()


@dp.callback_query_handler(lambda call: call.data.startswith("req_add_merch_"))
async def callback_add_merch_req_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    merch_id, req_id = call.data[len("req_add_merch_"):].split("_")
    req_id = int(req_id)
    db = SessionLocal()
    merch = crud.get_merch(db, merch_id)
    db.close()
    markup = call.message.reply_markup
    async with state.proxy() as data:
        req_data = data.setdefault(f"req_{req_id}", {})
        if not req_data:
            markup.add(InlineKeyboardButton("Принять", callback_data=f"req_accept_{req_id}"))

        req_data.setdefault("text", call.message.text)
        req_data.setdefault(merch.name, {"cost": 0, "count": 0, "id": merch_id})
        req_data.setdefault("sum", 0)
        req_data[merch.name]["cost"] += merch.cost
        req_data[merch.name]["count"] += 1
        req_data["sum"] += merch.cost
        data[f"req_{req_id}"] = req_data

    text = req_data["text"]
    text += "\n\nЗаказ:\n" + ''.join(
        [f"\n{key}: {val['count']}шт {val['cost']}" for key, val in req_data.items() if key != "sum" and key != "text"])
    text += f"\n\nСумма: {req_data['sum']}"

    await call.message.edit_text(text, reply_markup=markup)
    await call.answer()


@dp.callback_query_handler(lambda call: call.data.startswith("req_accept_"))
async def callback_accept_req_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    req_id = call.data[len("req_accept_"):]
    db = SessionLocal()
    requests = crud.get_shop_request(db, int(req_id))
    user = crud.get_user_by_chat(db, requests.chat_id)
    scores = crud.get_user_scores(db, user.id)
    cat_sc = [(crud.get_category(db, sc.category_id), sc) for sc in scores]
    db.close()
    buttons = [InlineKeyboardButton(cat.name, callback_data=f"req_final_{req_id}_{sc.category_id}") for cat, sc in
               cat_sc]
    buttons.append(InlineKeyboardButton("Отклонить", callback_data=f"req_reject_{req_id}"))
    markup = InlineKeyboardMarkup()
    markup.add(*buttons)
    await call.message.edit_reply_markup(reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data.startswith("req_final_"))
async def callback_accept_req_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    req_id, cat_id = call.data[len("req_final_"):].split("_")
    req_id = int(req_id)
    async with state.proxy() as data:
        req_data = data[f"req_{req_id}"]
    db = SessionLocal()
    requests = crud.get_shop_request(db, req_id)
    crud.update_shop_request_status(db, requests.id, "ACCEPTED")
    user = crud.get_user_by_chat(db, requests.chat_id)
    scores = crud.get_user_score(db, user.id, cat_id)

    new_counts = []
    for merch in req_data:
        if merch not in ("text", "sum"):
            merch_db = crud.get_merch(db, req_data[merch]["id"])
            if merch_db.count < req_data[merch]["count"]:
                db.close()
                await call.answer(f"Мерча {merch} осталось {merch_db.count}")
                return
            new_counts.append((merch_db.id, merch_db.count - req_data[merch]["count"]))

    if scores.score < req_data["sum"]:
        await call.answer("Недостаточно баллов")
        db.close()
        return
    crud.update_user_score(db, scores.users_id, scores.category_id, scores.score - req_data["sum"])
    for score in crud.get_user_scores(db, scores.users_id):
        if score.category_id != cat_id:
            crud.update_user_score_active(db, score.users_id, score.category_id, False)

    for merch_id, new_count in new_counts:
        crud.update_merch_count(db, merch_id, new_count)
    db.close()
    await call.answer()
    await call.message.delete()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
