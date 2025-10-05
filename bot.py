import os
import re
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
import db

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003084604599"))

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# ---------------------
# Валидация номера
# ---------------------
def validate_kz_phone(phone: str) -> tuple[bool, str]:
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    valid_codes = ['707', '775', '701', '702', '747', '705', '708',
                   '700', '776', '771', '778', '706', '777']

    if phone.startswith('+7'):
        phone = phone[2:]
    elif phone.startswith('8'):
        phone = phone[1:]
    elif phone.startswith('7') and len(phone) == 11:
        phone = phone[1:]

    if len(phone) != 10 or not phone.isdigit():
        return False, ""

    operator_code = phone[:3]
    if operator_code not in valid_codes:
        return False, ""

    return True, f"+7{phone}"

# ---------------------
# Состояния FSM
# ---------------------
class OrderStates(StatesGroup):
    waiting_trip_type = State()
    waiting_from = State()
    waiting_to = State()
    waiting_price = State()
    waiting_phone = State()

# ---------------------
# Клавиатуры
# ---------------------
def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🚕 Такси шақыру"))
    kb.add(types.KeyboardButton("📊 Менің тапсырыстарым"))
    return kb

def trip_type_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("🏙 Қала ішінде"))
    kb.add(types.KeyboardButton("🌄 Қаладан тыс"))
    kb.add(types.KeyboardButton("❌ Болдырмау"))
    return kb

def phone_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("📱 Телефонды жіберу", request_contact=True))
    kb.add(types.KeyboardButton("❌ Болдырмау"))
    return kb

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Болдырмау"))
    return kb

def accept_keyboard(order_id: int):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "🚕 Қабылдау", callback_data=f"accept_{order_id}"
    ))
    return keyboard

def complete_trip_keyboard(order_id: int):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "✅ Сапар аяқталды", callback_data=f"complete_{order_id}"
    ))
    return keyboard

def rating_keyboard(order_id: int):
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    for i in range(1, 6):
        keyboard.insert(types.InlineKeyboardButton(
            str(i) + "⭐", callback_data=f"rate_{order_id}_{i}"
        ))
    return keyboard

# ---------------------
# Команда /start
# ---------------------
@dp.message_handler(commands=['start'], state='*')
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "Сәлем! Такси шақыру үшін төмендегі батырманы басыңыз 👇",
        reply_markup=main_menu_kb()
    )

# ---------------------
# Отмена заказа
# ---------------------
@dp.message_handler(lambda m: m.text == "❌ Болдырмау", state='*')
async def cancel_order(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Тапсырыс болдырылмады", reply_markup=main_menu_kb())

# ---------------------
# Процесс заказа
# ---------------------
@dp.message_handler(lambda m: m.text == "🚕 Такси шақыру")
async def start_order(message: types.Message):
    await OrderStates.waiting_trip_type.set()
    await message.answer("Сапар түрін таңдаңыз:", reply_markup=trip_type_kb())

@dp.message_handler(state=OrderStates.waiting_trip_type)
async def get_trip_type(message: types.Message, state: FSMContext):
    if message.text == "🏙 Қала ішінде":
        trip_type = "city"
        trip_type_text = "🏙 Қала ішінде"
    elif message.text == "🌄 Қаладан тыс":
        trip_type = "intercity"
        trip_type_text = "🌄 Қаладан тыс"
    else:
        await message.answer("Сапар түрін таңдаңыз:", reply_markup=trip_type_kb())
        return

    await state.update_data(trip_type=trip_type, trip_type_text=trip_type_text)
    await OrderStates.waiting_from.set()
    await message.answer("Қай жерден кетесіз? (мекенжайды енгізіңіз)", reply_markup=cancel_kb())

@dp.message_handler(state=OrderStates.waiting_from)
async def get_from_addr(message: types.Message, state: FSMContext):
    await state.update_data(from_addr=message.text)
    await OrderStates.waiting_to.set()
    await message.answer("Қайда барасыз? (мекенжайды енгізіңіз)", reply_markup=cancel_kb())

@dp.message_handler(state=OrderStates.waiting_to)
async def get_to_addr(message: types.Message, state: FSMContext):
    await state.update_data(to_addr=message.text)
    await OrderStates.waiting_price.set()
    data = await state.get_data()
    trip_type = data.get('trip_type', 'city')
    price_hint = "Мысал: 500, 700, 1000" if trip_type == 'city' else "Мысал: 2000, 3000, 5000"
    await message.answer(
        f"💰 Өзіңіздің баға ұсынысыңызды жазыңыз (теңгемен):\n\n{price_hint}",
        reply_markup=cancel_kb()
    )

@dp.message_handler(state=OrderStates.waiting_price)
async def get_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price < 100 or price > 100000:
            raise ValueError
    except ValueError:
        await message.answer("❌ Қате формат! 100-100000 теңге аралығында сан енгізіңіз.", reply_markup=cancel_kb())
        return

    await state.update_data(price=price)
    await OrderStates.waiting_phone.set()
    await message.answer(
        "Телефон нөміріңізді жіберіңіз:\n📱 Қазақстандық нөмір енгізіңіз.",
        reply_markup=phone_kb()
    )

@dp.message_handler(content_types=types.ContentType.CONTACT, state=OrderStates.waiting_phone)
async def get_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    is_valid, cleaned_phone = validate_kz_phone(phone)
    if not is_valid:
        await message.answer("❌ Қате нөмір! Қайта жіберіңіз.", reply_markup=phone_kb())
        return
    await process_phone(message, state, cleaned_phone)

@dp.message_handler(state=OrderStates.waiting_phone)
async def get_phone_text(message: types.Message, state: FSMContext):
    phone = message.text
    is_valid, cleaned_phone = validate_kz_phone(phone)
    if not is_valid:
        await message.answer("❌ Қате нөмір! Қайта жіберіңіз.", reply_markup=phone_kb())
        return
    await process_phone(message, state, cleaned_phone)

async def process_phone(message: types.Message, state: FSMContext, phone: str):
    data = await state.get_data()
    order_id = await db.insert_order(
        data['from_addr'], data['to_addr'], data['price'], phone, message.from_user.id, data.get('trip_type', 'city')
    )
    msg = await bot.send_message(
        GROUP_ID,
        f"🚕 Жаңа тапсырыс #{order_id}\n📍 {data['from_addr']} → {data['to_addr']}\n💰 {data['price']} ₸\n📱 {phone}",
        reply_markup=accept_keyboard(order_id)
    )
    await db.update_group_message_id(order_id, msg.message_id)
    await state.finish()
    await message.answer("✅ Тапсырыс жіберілді!", reply_markup=main_menu_kb())

# ---------------------
# Обработка callback-ов
# ---------------------
@dp.callback_query_handler(lambda c: c.data.startswith("accept_"))
async def callback_accept(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    driver_id = callback.from_user.id
    driver_name = callback.from_user.full_name or callback.from_user.username or "Жүргізуші"
    ok = await db.try_accept_order(order_id, driver_id)
    order = await db.get_order(order_id)
    if not order or not ok:
        await callback.answer("Бұл тапсырыс қабылданған.", show_alert=True)
        return
    await bot.send_message(driver_id, f"✅ Сіз тапсырысты қабылдадыңыз #{order_id}")
    await callback.answer("Тапсырыс қабылданды!")

# ---------------------
# Запуск через polling
# ---------------------
async def on_startup(_):
    await db.init_db()
    print("✅ База данных инициализирована!")

async def on_shutdown(_):
    print("🛑 Бот өшірілді.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
