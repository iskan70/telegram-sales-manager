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

TOKEN = "8405594915:AAG7xBp4bUsxZLd9_oBwuukL0Z2ZB2IZpH4"
ADMIN_ID = 494255577

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

@dp.message(Command("start"))
async def start(message: types.Message):
    text = (
        "<b>Привет! Я — менеджер компании по логистике из Китая в Россию</b> 🚚\n\n"
        "Мы помогаем с перевозками грузов, выкупом товаров на 1688/Taobao/Poizon и поиском поставщиков.\n\n"
        "Расскажите, что вас интересует — рассчитаю стоимость и условия!"
    )
    await message.answer(text, reply_markup=main_kb)

@dp.message(F.text == "Узнать об услугах 🚚")
async def services(message: types.Message):
    text = (
        "Наши услуги:\n\n"
        "• <b>Перевозки</b> — море, авиа, ж/д, авто от двери до двери\n"
        "• <b>Выкуп товаров</b> — покупаем от вашего имени на китайских площадках\n"
        "• <b>Поиск поставщиков</b> — находим и проверяем фабрики\n\n"
        "Напишите детали — сделаю точный расчёт!"
    )
    await message.answer(text, reply_markup=main_kb)

@dp.message(F.text == "Оставить заявку 📝")
async def start_form(message: types.Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer("Как к вам обращаться? (введите имя)", reply_markup=ReplyKeyboardRemove())

@dp.message(LeadForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(LeadForm.phone)
    await message.answer("Ваш телефон или Telegram для связи:")

@dp.message(LeadForm.phone)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await state.set_state(LeadForm.service)
    await message.answer("Какая услуга вас интересует? (перевозка, выкуп, поиск поставщиков)")

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

    await message.answer("✅ Заявка принята! Скоро свяжусь с расчётом.", reply_markup=main_kb)

    admin_text = (
        f"<b>Новая заявка от менеджера-бота!</b>\n\n"
        f"Имя: {data['name']}\n"
        f"Контакт: {data['phone']}\n"
        f"Услуга: {data['service']}\n"
        f"Детали: {data['details']}\n\n"
        f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'нет'})"
    )
    await bot.send_message(ADMIN_ID, admin_text)

@dp.message()
async def free_chat(message: types.Message):
    text = "Расскажите подробнее — помогу с расчётом и условиями доставки! 🚚"
    await message.answer(text, reply_markup=main_kb)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
