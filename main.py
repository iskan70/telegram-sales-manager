import asyncio
import logging
import requests
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Загрузка переменных (для локального теста из .env, на Render возьмет из системы)
load_dotenv()

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = 494255577  # ID того, кто получает заявки

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
defaults = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=TOKEN, default=defaults)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# --- СОСТОЯНИЯ (FSM) ---
class LeadForm(StatesGroup):
    name = State()
    phone = State()
    details = State()

# --- КЛАВИАТУРЫ ---
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🌍 Услуги и направления"), KeyboardButton(text="📊 Рассчитать стоимость")],
    [KeyboardButton(text="📝 Оставить заявку"), KeyboardButton(text="👨‍💼 Менеджер")]
], resize_keyboard=True)

directions_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇨🇳 Китай (Авто/Море/Выкуп)", callback_data="dir_china")],
    [InlineKeyboardButton(text="🇹🇷 Турция / 🇦🇪 ОАЭ", callback_data="dir_east")],
    [InlineKeyboardButton(text="🇪🇺 Европа / СНГ", callback_data="dir_europe")]
])

# --- ЛОГИКА ИИ ---
system_prompt = """
Ты — ведущий менеджер международной логистической компании "Global Logistics Manager".
Мы занимаемся доставкой грузов по всему миру (Китай, Европа, Турция, ОАЭ, СНГ).

Твои задачи:
- Если клиент не уточнил страну, спроси: "Из какой страны планируете доставку?".
- Предлагай автомобильный транспорт как самый гибкий и популярный вариант.
- Ты эксперт в логистике: понимаешь, что такое вес, объем, таможня и выкуп товаров.
- Отвечай дружелюбно, профессионально, используй эмодзи.
- Твоя цель — помочь клиенту и подвести его к оформлению заявки.
- Ты помнишь контекст беседы.
"""

conversation_history = {}

def get_ai_response(user_id, user_message):
    if user_id not in conversation_history:
        conversation_history[user_id] = [{"role": "system", "content": system_prompt}]

    conversation_history[user_id].append({"role": "user", "content": user_message})

    # Ограничение истории (последние 10 сообщений) для экономии токенов
    if len(conversation_history[user_id]) > 10:
        conversation_history[user_id] = [conversation_history[user_id][0]] + conversation_history[user_id][-9:]

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    data = {
        "model": "gpt-4o-mini",
        "messages": conversation_history[user_id],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=25)
        response.raise_for_status()
        res_json = response.json()
        assistant_message = res_json["choices"][0]["message"]["content"]
        conversation_history[user_id].append({"role": "assistant", "content": assistant_message})
        return assistant_message
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        return "Я готов ответить на ваши вопросы по логистике! Опишите ваш груз, и я помогу с расчетом. 😊"

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        f"<b>Здравствуйте, {message.from_user.first_name}! 🌍</b>\n\n"
        "Я — ваш интеллектуальный помощник <b>Logistics Manager</b>.\n\n"
        "Помогу организовать доставку и таможню грузов из любой точки мира:\n"
        "• <b>Китай</b> (выкуп, авто, море)\n"
        "• <b>Турция и ОАЭ</b>\n"
        "• <b>Европа и СНГ</b>\n\n"
        "Задайте мне вопрос в чате или выберите пункт меню ниже. 👇"
    )
    await message.answer(welcome_text, reply_markup=main_kb)

@dp.message(F.text == "🌍 Услуги и направления")
async def show_services(message: types.Message):
    await message.answer("Выберите интересующее вас направление для консультации:", reply_markup=directions_kb)

@dp.callback_query(F.data.startswith("dir_"))
async def direction_callback(callback: types.CallbackQuery):
    prompts = {
        "dir_china": "Расскажи подробно про логистику из Китая, авто-доставку и выкуп товаров.",
        "dir_east": "Расскажи про логистику из Турции и ОАЭ.",
        "dir_europe": "Расскажи про доставку из Европы и СНГ в текущих условиях."
    }
    response = get_ai_response(callback.from_user.id, prompts.get(callback.data))
    await callback.message.answer(response)
    await callback.answer()

@dp.message(F.text == "📊 Рассчитать стоимость")
async def calc_info(message: types.Message):
    await message.answer(
        "Для расчета стоимости мне нужно знать:\n"
        "1. Маршрут (откуда/куда)\n"
        "2. Характеристики груза (вес, объем, тип товара)\n\n"
        "Напишите эти данные здесь или нажмите <b>'Оставить заявку'</b>."
    )

@dp.message(F.text == "👨‍💼 Менеджер")
async def contact_manager(message: types.Message):
    await message.answer("По всем важным вопросам вы можете написать нашему старшему менеджеру: @Ваш_Юзернейм")

# --- ФОРМА ЗАЯВКИ ---

@dp.message(F.text == "📝 Оставить заявку")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer("Как к вам обращаться?", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(LeadForm.phone)
    # Кнопка запроса контакта
    contact_kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📱 Отправить контакт", request_contact=True)]
    ], resize_keyboard=True)
    await message.answer("Нажмите кнопку ниже, чтобы передать номер телефона для связи:", reply_markup=contact_kb)

@dp.message(LeadForm.phone, F.contact | F.text)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    await state.set_state(LeadForm.details)
    await message.answer("Опишите детали (товар, вес, маршрут):", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.details)
async def get_details(message: types.Message, state: FSMContext):
    data = await state.get_data()
    details = message.text
    await state.clear()

    await message.answer("✅ <b>Заявка принята!</b>\nМенеджер свяжется с вами в ближайшее время для точного расчета.", reply_markup=main_kb)

    admin_report = (
        f"🔥 <b>НОВАЯ ЗАЯВКА</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📞 <b>Тел:</b> {data['phone']}\n"
        f"📦 <b>Груз:</b> {details}\n"
        f"🤖 <b>Юзер:</b> @{message.from_user.username or '—'}\n"
        f"━━━━━━━━━━━━━━"
    )
    await bot.send_message(ADMIN_ID, admin_report)

# --- ОБЩИЙ ЧАТ С ИИ ---
@dp.message()
async def chat_handler(message: types.Message):
    if not message.text: return
    # Эффект "печатает..."
    await bot.send_chat_action(message.chat.id, "typing")
    response = get_ai_response(message.from_user.id, message.text)
    await message.answer(response)

# --- ЗАПУСК ---
async def main():
    logging.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Stopped")
