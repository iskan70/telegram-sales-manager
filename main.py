from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio
import logging
import requests
import os

TOKEN = "8405594915:AAG7xBp4bUsxZLd9_oBwuukL0Z2ZB2IZpH4"
ADMIN_ID = 494255577

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_1")

if not OPENAI_API_KEY:
    logging.error("OPENAI_API_KEY_1 не найден!")
    exit(1)

defaults = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=TOKEN, default=defaults)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)

class LeadForm(StatesGroup):
    name = State()
    phone = State()
    service = State()
    details = State()

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Узнать об услугах 🚚")],
    [KeyboardButton(text="Оставить заявку 📝")]
], resize_keyboard=True)

# Обновлённый system prompt — авто-перевозки на первом месте
system_prompt = """
Ты — опытный менеджер по продажам компании по логистике из Китая в Россию.
Самый востребованный вариант сейчас — автомобильные грузовые перевозки (быстро, гибко, выгодная цена).

Компания занимается:
- Автомобильными грузовыми перевозками (основной и самый популярный способ)
- Морскими, авиа и ж/д перевозками
- Выкупом товаров на 1688, Taobao, Poizon
- Поиском и проверкой поставщиков

Отвечай как живой человек: дружелюбно, профессионально, используй эмодзи, задавай уточняющие вопросы.
Никогда не говори, что ты бот. Веди диалог естественно.
Если клиент интересуется перевозкой — в первую очередь предлагай автомобильный транспорт как самый востребованный.
Помни весь предыдущий контекст разговора.
"""

# Хранение истории диалога по user_id
conversation_history = {}

def get_ai_response(user_id, user_message):
    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": system_prompt}]

    conversation_history[user_id].append({"role": "user", "content": user_message})

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    data = {
        "model": "gpt-4o-mini",
        "messages": conversation_history[user_id],
        "temperature": 0.8,
        "max_tokens": 600
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        assistant_message = response.json()["choices"][0]["message"]["content"]

        conversation_history[user_id].append({"role": "assistant", "content": assistant_message})

        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = [conversation_history[user_id][0]] + conversation_history[user_id][-19:]

        return assistant_message
    except Exception as e:
        logging.error(f"Ошибка OpenAI API: {e}")
        return "Извините, сейчас небольшая задержка. Расскажите подробнее — помогу с расчётом! 😊"

@dp.message(Command("start"))
async def start(message: types.Message):
    text = get_ai_response(message.from_user.id, "Приветствие для нового клиента")
    await message.answer(text, reply_markup=main_kb)

@dp.message(F.text == "Узнать об услугах 🚚")
async def services(message: types.Message):
    text = get_ai_response(message.from_user.id, "Расскажи об услугах компании подробно, особенно про автомобильные грузовые перевозки как самый востребованный вариант")
    await message.answer(text, reply_markup=main_kb)

@dp.message(F.text == "Оставить заявку 📝")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer("Как к вам обращаться?", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(LeadForm.phone)
    await message.answer("Ваш телефон для связи:")

@dp.message(LeadForm.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(LeadForm.service)
    await message.answer("Какая услуга вас интересует? (перевозка, выкуп товаров, поиск поставщиков)")

@dp.message(LeadForm.service)
async def get_service(message: types.Message, state: FSMContext):
    await state.update_data(service=message.text.strip())
    await state.set_state(LeadForm.details)
    await message.answer("Опишите детали заказа (товар, объём, маршрут, бюджет):")

@dp.message(LeadForm.details)
async def get_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text.strip())
    data = await state.get_data()
    await state.clear()

    await message.answer("✅ Спасибо! Заявка принята. Скоро свяжусь с расчётом!", reply_markup=main_kb)

    admin_text = (
        f"<b>Новая заявка от бота-менеджера!</b>\n\n"
        f"Имя: {data['name']}\n"
        f"Контакт: {data['phone']}\n"
        f"Услуга: {data['service']}\n"
        f"Детали: {data['details']}\n\n"
        f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'нет'})"
    )
    await bot.send_message(ADMIN_ID, admin_text)

@dp.message()
async def free_chat(message: types.Message):
    response = get_ai_response(message.from_user.id, message.text)
    await message.answer(response, reply_markup=main_kb)

async def main():
    logging.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
