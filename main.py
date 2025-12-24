from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio
import logging
import requests
import os

# --- НАСТРОЙКИ ---
TOKEN = "8405594915:AAH86zSfvyPO0u-FAmRnCKhAue4hi9ex4vk"
ADMIN_ID = 494255577
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY_1")

defaults = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=TOKEN, default=defaults)
storage = MemoryStorage() # Для продажи лучше сменить на Redis или БД
dp = Dispatcher(storage=storage)

# --- КЛАВИАТУРЫ ---
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🚛 Рассчитать доставку"), KeyboardButton(text="📝 Оставить заявку")],
    [KeyboardButton(text="❓ Часто задаваемые вопросы"), KeyboardButton(text="👨‍💼 Связь с менеджером")]
], resize_keyboard=True)

# Инлайн-кнопки для выбора типа услуги (выглядит круче)
services_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚗 Авто-доставка (Хит!)", callback_data="serv_auto")],
    [InlineKeyboardButton(text="🚢 Море / ✈️ Авиа", callback_data="serv_other")],
    [InlineKeyboardButton(text="🛍 Выкуп с 1688/Poizon", callback_data="serv_buy")]
])

class LeadForm(StatesGroup):
    name = State()
    phone = State()
    details = State()

# --- ЛОГИКА ИИ ---
system_prompt = """Ты — премиальный менеджер компании China Logistics Manager... (твой промпт)"""
conversation_history = {}

def get_ai_response(user_id, user_message):
    # Твоя функция без изменений, но добавь ограничение контекста
    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": system_prompt}]
    
    conversation_history[user_id].append({"role": "user", "content": user_message})
    
    # Очистка старой истории (оставляем последние 10 сообщений для экономии токенов)
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = [conversation_history[user_id][0]] + conversation_history[user_id][-9:]

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": conversation_history[user_id],
                "temperature": 0.7
            },
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=20
        )
        return response.json()["choices"][0]["message"]["content"]
    except:
        return "Произошла ошибка, но я готов обсудить вашу доставку! Что везем?"

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    welcome_text = (
        f"<b>Нихао, {message.from_user.first_name}! 🇨🇳</b>\n\n"
        "Я — ваш интеллектуальный помощник <b>China Logistics Manager</b>.\n"
        "Помогу привезти груз из Китая в РФ быстро и без лишней бюрократии.\n\n"
        "Чем могу помочь сегодня?"
    )
    await message.answer(welcome_text, reply_markup=main_kb)

@dp.message(F.text == "🚛 Рассчитать доставку")
async def calc_delivery(message: types.Message):
    await message.answer("Выберите интересующий способ доставки:", reply_markup=services_inline_kb)

@dp.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer("Как к вам обращаться?", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(LeadForm.phone)
    # Запрос контакта кнопкой (Очень удобно для юзера)
    contact_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]
    ], resize_keyboard=True)
    await message.answer("Нажмите на кнопку ниже, чтобы отправить номер телефона:", reply_markup=contact_kb)

@dp.message(LeadForm.phone, F.contact | F.text)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(LeadForm.details)
    await message.answer("Опишите ваш груз (товар, вес, объем):", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.details)
async def get_details(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    # Подтверждение пользователю
    await message.answer("✅ <b>Заявка принята!</b>\nМенеджер свяжется с вами в течение 15 минут.", reply_markup=main_kb)

    # Уведомление админу (красивое)
    admin_text = (
        f"🔥 <b>НОВАЯ ЗАЯВКА</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📞 <b>Тел:</b> {data['phone']}\n"
        f"📦 <b>Груз:</b> {message.text}\n"
        f"🤖 <b>Юзер:</b> @{message.from_user.username}\n"
        f"━━━━━━━━━━━━━━"
    )
    await bot.send_message(ADMIN_ID, admin_text)

@dp.message()
async def chat_ai(message: types.Message):
    # Показываем статус "печатает", чтобы ожидание ИИ было естественным
    await bot.send_chat_action(message.chat.id, "typing")
    response = get_ai_response(message.from_user.id, message.text)
    await message.answer(response)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
