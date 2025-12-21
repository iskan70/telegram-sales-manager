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

# Токен бота
TOKEN = "8405594915:AAG7xBp4bUsxZLd9_oBwuukL0Z2ZB2IZpH4"
ADMIN_ID = 494255577  # твой ID для уведомлений

# Твой Grok API ключ
GROK_API_KEY = "xai-gVBpGHQqMtFLjJJIVdSEbJnLcDMg3vPci6uaMvTLrgUT3ltUAQI4ljB8J6sVEg7CXqe1FJ1laTK044lQ"

defaults = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=TOKEN, default=defaults)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)

# Состояния для формы заявки
class LeadForm(StatesGroup):
    name = State()
    phone = State()
    service = State()
    details = State()

# Клавиатура
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Узнать об услугах 🚚")],
    [KeyboardButton(text="Оставить заявку 📝")]
], resize_keyboard=True)

# System prompt — "обучение" бота (меняй здесь, чтобы обучать)
system_prompt = """
Ты — опытный менеджер по продажам компании по логистике из Китая в Россию.
Компания занимается перевозками грузов (море, авиа, ж/д, авто), выкупом товаров на 1688, Taobao, Poizon и поиском поставщиков.

Отвечай как живой человек: дружелюбно, профессионально, используй эмодзи, задавай уточняющие вопросы, подстраивайся под клиента.
Никогда не говори, что ты бот. Веди диалог естественно.
Если клиент готов — собери имя, телефон, услугу и детали заказа.
"""

def get_ai_response(user_message, history=""):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}"}
    data = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": system_prompt + history},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.8,  # для живости ответов
        "max_tokens": 500
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "Извините, сейчас небольшая задержка. Расскажите подробнее — помогу с расчётом!"
    except:
        return "Техническая пауза. Продолжим? 😊"

@dp.message(Command("start"))
async def start(message: types.Message):
    text = get_ai_response("Приветствие для нового клиента")
    await message.answer(text, reply_markup=main_kb)

@dp.message(F.text == "Узнать об услугах 🚚")
async def services(message: types.Message):
    text = get_ai_response("Расскажи об услугах компании")
    await message.answer(text, reply_markup=main_kb)

@dp.message(F.text == "Оставить заявку 📝")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer("Как к вам обращаться?", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(LeadForm.phone)
    await message.answer("Ваш телефон или Telegram для связи:")

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

# Свободный диалог — любые сообщения идут в Grok
@dp.message()
async def free_chat(message: types.Message):
    response = get_ai_response(message.text)
    await message.answer(response, reply_markup=main_kb)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
