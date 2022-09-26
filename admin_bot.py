import json
from functools import reduce

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Filter
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ContentType

import crud
import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# db = SessionLocal()
# db.close()


class IsAdmin(Filter):
    key = "is_admin"

    async def check(self, message: types.Message):
        return message.from_user.id == 427592297

# TODO move token to env

with open("admin_config.json", "r") as f:
    config = json.load(f)

storage = MemoryStorage()
bot = Bot(config["API_key"])
dp = Dispatcher(bot, storage=storage)
QUESTION_LINK = "https://t.me/hdl_7bits_bot?start="


class AddCategoryStates(StatesGroup):
    add_category = State()


class AddQuestionStates(StatesGroup):
    add_question_name = State()
    add_question_category = State()
    add_question_text = State()
    add_question_answer_count = State()
    add_question_correct_answers = State()
    add_question_score = State()


class AddMerchStates(StatesGroup):
    add_merch_name = State()
    add_merch_cost = State()
    add_merch_count = State()


class UpdateMerchStates(StatesGroup):
    update_merch_cost = State()
    update_merch_count = State()


async def generate_markup_with_menu():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Вернуться в меню", callback_data="menu"))
    return markup


@dp.message_handler(IsAdmin(), commands=['start'])
async def handle_start_message(message: Message, *args, **kwargs):
    await message.answer(message.from_user.id)
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("Показать категории", callback_data="cat_show"),
        InlineKeyboardButton("Добавить категорию", callback_data="cat_add"),
        InlineKeyboardButton("Удалить категорию", callback_data="cat_delete"),
        InlineKeyboardButton("Показать вопросы", callback_data="ques_show"),
        InlineKeyboardButton("Добавить вопрос", callback_data="ques_add"),
        InlineKeyboardButton("Удалить вопрос", callback_data="ques_delete"),
        InlineKeyboardButton("Показать мерч", callback_data="merch_show"),
        InlineKeyboardButton("Добавить мерч", callback_data="merch_add"),
        InlineKeyboardButton("Удалить мерч", callback_data="merch_delete"),
    )
    await message.answer("Функции", reply_markup=markup)


@dp.message_handler(IsAdmin(), state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext, *args, **kwargs):
    current_state = await state.get_state()
    if current_state is None:
        await handle_start_message(message, state)
        return

    await state.finish()
    await handle_start_message(message, state)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("menu"), state="*")
async def callback_menu_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    current_state = await state.get_state()

    async with state.proxy() as data:
        data.clear()

    if current_state is None:
        await handle_start_message(call.message, state)
        return

    await state.finish()
    await handle_start_message(call.message, state)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("cat_"))
async def callback_category_query(call: CallbackQuery, *args, **kwargs):
    markup = await generate_markup_with_menu()
    if call.data == "cat_show":
        db = SessionLocal()
        categories = crud.get_categories(db)
        db.close()
        str_cats = '\n'.join(map(lambda c: c.name, categories))
        reply = f"Доступные категории вопросов:\n{str_cats}"
        await call.message.answer(reply, reply_markup=markup)
        return

    elif call.data == "cat_add":
        await AddCategoryStates.add_category.set()
        await call.message.answer("Введите название категории вопросов", reply_markup=markup)
        return

    elif call.data == "cat_delete":
        db = SessionLocal()
        categories = crud.get_categories(db)
        db.close()
        cat_buttons = [InlineKeyboardButton(cat.name, callback_data="dl_cat_" + str(cat.id)) for cat in categories]
        markup.row_width = 1
        markup.add(*cat_buttons)
        await call.message.answer("Выберите категорию, которую хотите удалить", reply_markup=markup)
        return

    await call.answer()


@dp.message_handler(IsAdmin(), state=AddCategoryStates.add_category)
async def process_add_category_name_step(message: Message, state: FSMContext, **kwargs):
    db = SessionLocal()
    category = crud.create_category(db, message.text)
    db.close()
    await state.finish()
    reply = f"Категория вопросов \"{category.name}\" создана"
    await message.answer(reply)
    await handle_start_message(message, state)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("dl_cat_"))
async def callback_delete_category_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    cat_id = call.data[len("dl_cat_"):]
    db = SessionLocal()
    crud.delete_category(db, cat_id)
    db.close()
    markup = call.message.reply_markup
    buttons = reduce(lambda x, y: x + y, markup.inline_keyboard)
    buttons = list(filter(lambda x: x.callback_data != call.data, buttons))
    markup.inline_keyboard.clear()
    markup.row_width = 1
    markup.add(*buttons)
    await call.message.edit_reply_markup(reply_markup=markup)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("ques_"))
async def callback_question_query(call: CallbackQuery, *args, **kwargs):
    markup = await generate_markup_with_menu()

    if call.data == "ques_show":
        db = SessionLocal()
        questions = crud.get_questions(db)
        db.close()
        buttons = [InlineKeyboardButton(q.name, callback_data="get_ques_" + str(q.id)) for q in questions]
        markup.row_width = 1
        markup.add(*buttons)
        reply = f"Доступные вопросы:"
        await call.message.answer(reply, reply_markup=markup)

    elif call.data == "ques_add":
        await AddQuestionStates.add_question_name.set()
        await call.message.answer("Введите название вопроса", reply_markup=markup)
        return

    elif call.data == "ques_delete":
        db = SessionLocal()
        questions = crud.get_questions(db)
        db.close()
        buttons = [InlineKeyboardButton(q.name, callback_data="dl_ques_" + str(q.id)) for q in questions]
        markup.row_width = 1
        markup.add(*buttons)
        await call.message.answer("Выберите вопрос, который хотите удалить", reply_markup=markup)
        return

    await call.answer()


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("get_ques_"))
async def callback_get_question_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    ques_id = call.data[len("get_ques_"):]
    db = SessionLocal()
    question = crud.get_question(db, ques_id)
    db.close()
    link = QUESTION_LINK + str(question.id)
    reply = f"{question.name}\n\n{question.text}\nВарианты: {', '.join(map(str, question.answers))}\nПравильные ответы: {', '.join(map(str, question.cor_answers))}\n\n{link}"
    if question.photo:
        await bot.send_photo(
            call.message.chat.id,
            question.photo,
            caption=reply
        )
    else:
        await call.message.answer(reply)
    await handle_start_message(call.message, state)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("dl_ques_"))
async def callback_delete_question_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    ques_id = call.data[len("dl_ques_"):]
    db = SessionLocal()
    crud.delete_question(db, ques_id)
    db.close()
    markup = call.message.reply_markup
    buttons = reduce(lambda x, y: x + y, markup.inline_keyboard)
    buttons = list(filter(lambda x: x.callback_data != call.data, buttons))
    markup.inline_keyboard.clear()
    markup.row_width = 1
    markup.add(*buttons)
    await call.message.edit_reply_markup(reply_markup=markup)


@dp.message_handler(IsAdmin(), state=AddQuestionStates.add_question_name)
async def add_question_name_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()
    db = SessionLocal()

    categories = crud.get_categories(db)
    db.close()
    async with state.proxy() as data:
        data["name"] = message.text

    await AddQuestionStates.next()
    buttons = [InlineKeyboardButton(c.name, callback_data=f"add_ques_cat_{c.id}") for c in categories]
    markup.row_width = 1
    markup.add(*buttons)
    await message.answer(
        f"Выберите категорию вопроса",
        reply_markup=markup
    )


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("add_ques_cat_"),
                           state=AddQuestionStates.add_question_category)
async def process_add_question_category_step(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    cat_i = call.data[len("add_ques_cat_"):]

    async with state.proxy() as data:
        data["category"] = cat_i

    await AddQuestionStates.next()
    await call.message.answer(
        """Введите текст вопроса (к сообщению можно прикрепить одну фотографию).
        Тут же нужно указать варианты ответов в формате
        1. Ответ 1
        2. Ответ 2
        3. Ответ 3""",
        reply_markup=markup
    )


@dp.message_handler(IsAdmin(), state=AddQuestionStates.add_question_text, content_types=[ContentType.PHOTO, ContentType.TEXT])
async def process_add_question_text_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    async with state.proxy() as data:
        data["text"] = message.text if not message.photo else message.caption
        data["photo_id"] = message.photo[-1].file_id if message.photo else None

    await AddQuestionStates.next()
    await message.answer("Введите кол-во вариантов ответа", reply_markup=markup)


@dp.message_handler(IsAdmin(), state=AddQuestionStates.add_question_answer_count)
async def process_add_question_answer_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    async with state.proxy() as data:
        data["answers"] = [str(i) for i in range(1, int(message.text) + 1)]

    await AddQuestionStates.next()
    await message.answer(
        "Напишите правильные варианты через запятую. Пример: 1, 2, 3",
        reply_markup=markup
    )


@dp.message_handler(IsAdmin(), state=AddQuestionStates.add_question_correct_answers)
async def process_add_question_cor_answer_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    async with state.proxy() as data:
        data["cor_answers"] = message.text.strip().replace(", ", ",").split(",")

    await AddQuestionStates.next()
    await message.answer(
        f"Сколько баллов дается за вопрос?",
        reply_markup=markup
    )


@dp.message_handler(IsAdmin(), state=AddQuestionStates.add_question_score)
async def process_add_question_score_step(message: Message, state: FSMContext, *args, **kwargs):
    async with state.proxy() as data:
        data["score"] = int(message.text)

        image = None
        if data["photo_id"]:
            file = await bot.get_file(data["photo_id"])
            file_path = file.file_path
            image = await bot.download_file(file_path)
            image = image.read()

        db = SessionLocal()
        question = crud.create_question(
            db,
            name=data["name"],
            text=data["text"],
            photo=image,
            answers=data["answers"],
            cor_answers=data["cor_answers"],
            score=data["score"],
            category_id=data["category"]
        )
        db.close()

    link = QUESTION_LINK + str(question.id)

    await message.answer(
        f"Ссылка на вопрос: {link}"
    )
    await state.finish()
    await handle_start_message(message, state)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("merch_"))
async def callback_merch_query(call: CallbackQuery, *args, **kwargs):
    markup = await generate_markup_with_menu()

    if call.data == "merch_show":
        db = SessionLocal()
        merch = crud.get_all_merch(db)
        db.close()
        buttons = [
            InlineKeyboardButton(
                f"{m.name}: {m.cost} очков, {m.count} шт",
                callback_data="get_merch_" + str(m.id)
            )
            for m in merch
        ]
        markup.row_width = 1
        markup.add(*buttons)
        reply = f"Доступный мерч:"
        await call.message.answer(reply, reply_markup=markup)

    elif call.data == "merch_add":
        await AddMerchStates.add_merch_name.set()
        await call.message.answer("Введите название мерча", reply_markup=markup)
        return

    elif call.data == "merch_delete":
        db = SessionLocal()
        merch = crud.get_all_merch(db)
        db.close()
        buttons = [InlineKeyboardButton(m.name, callback_data="dl_merch_" + str(m.id)) for m in merch]
        markup.row_width = 1
        markup.add(*buttons)
        await call.message.answer("Выберите мерч, который хотите удалить", reply_markup=markup)
        return

    await call.answer()


@dp.message_handler(IsAdmin(), state=AddMerchStates.add_merch_name)
async def add_merch_name_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    async with state.proxy() as data:
        data["name"] = message.text

    await AddMerchStates.next()
    await message.answer(
        f"Введите стоимость мерча",
        reply_markup=markup
    )


@dp.message_handler(IsAdmin(), state=AddMerchStates.add_merch_cost)
async def add_merch_cost_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    async with state.proxy() as data:
        data["cost"] = int(message.text)

    await AddMerchStates.next()
    await message.answer(
        f"Введите количество мерча",
        reply_markup=markup
    )


@dp.message_handler(IsAdmin(), state=AddMerchStates.add_merch_count)
async def add_merch_count_step(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()
    count = int(message.text)

    async with state.proxy() as data:
        name, cost = data["name"], data["cost"]

    db = SessionLocal()
    crud.create_merch(db, name, cost, count)
    db.close()

    await state.finish()
    await message.answer(
        f"Мерч добавлен",
        reply_markup=markup
    )
    await handle_start_message(message, state)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("dl_merch_"))
async def callback_delete_merch_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    merch_id = call.data[len("dl_merch_"):]
    db = SessionLocal()
    crud.delete_merch(db, merch_id)
    db.close()
    markup = call.message.reply_markup
    buttons = reduce(lambda x, y: x + y, markup.inline_keyboard)
    buttons = list(filter(lambda x: x.callback_data != call.data, buttons))
    markup.inline_keyboard.clear()
    markup.row_width = 1
    markup.add(*buttons)
    await call.message.edit_reply_markup(reply_markup=markup)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("get_merch_"))
async def callback_get_merch_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    merch_id = call.data[len("get_merch_"):]
    db = SessionLocal()
    merch = crud.get_merch(db, merch_id)
    db.close()
    reply = f"{merch.name}: {merch.cost} очков, {merch.count} шт"

    buttons = [
        InlineKeyboardButton("Изменить стоимость", callback_data=f"upd_merch_cost_{merch_id}"),
        InlineKeyboardButton("Изменить количество", callback_data=f"upd_merch_count_{merch_id}"),
    ]
    markup.add(*buttons)
    await call.message.answer(reply, reply_markup=markup)


@dp.callback_query_handler(IsAdmin(), lambda call: call.data.startswith("upd_merch_"))
async def callback_update_merch_query(call: CallbackQuery, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()

    if call.data.startswith("upd_merch_cost_"):
        merch_id = call.data[len("upd_merch_cost_"):]
        async with state.proxy() as data:
            data["merch_id"] = merch_id

        reply = "Введите новую стоимость"
        await UpdateMerchStates.update_merch_cost.set()
        await call.message.answer(reply, reply_markup=markup)

    elif call.data.startswith("upd_merch_count_"):
        merch_id = call.data[len("upd_merch_count_"):]
        async with state.proxy() as data:
            data["merch_id"] = merch_id

        reply = "Введите новое количество"
        await UpdateMerchStates.update_merch_count.set()
        await call.message.answer(reply, reply_markup=markup)

    await call.answer()


@dp.message_handler(IsAdmin(), state=UpdateMerchStates.update_merch_cost)
async def callback_update_merch_cost(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()
    cost = int(message.text)

    async with state.proxy() as data:
        merch_id = data["merch_id"]

    db = SessionLocal()
    crud.update_merch_cost(db, merch_id, cost)
    db.close()

    await state.finish()
    await message.answer(
        f"Мерч обновлен",
        reply_markup=markup
    )
    await handle_start_message(message, state)


@dp.message_handler(IsAdmin(), state=UpdateMerchStates.update_merch_count)
async def callback_update_merch_count(message: Message, state: FSMContext, *args, **kwargs):
    markup = await generate_markup_with_menu()
    count = int(message.text)

    async with state.proxy() as data:
        merch_id = data["merch_id"]

    db = SessionLocal()
    crud.update_merch_count(db, merch_id, count)
    db.close()

    await state.finish()
    await message.answer(
        f"Мерч обновлен",
        reply_markup=markup
    )
    await handle_start_message(message, state)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
