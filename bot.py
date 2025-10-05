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
    """
    Валидирует казахстанский номер телефона.
    Возвращает (True, очищенный_номер) или (False, "")
    """
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    valid_codes = ['707', '775', '701', '702', '747', '705', '708', 
                   '700', '776', '771', '778', '706', '777']
    
    if phone.startswith('+7'):
        phone = phone[2:]
    elif phone.startswith('8'):
        phone = phone[1:]
    elif phone.startswith('7') and len(phone) == 11:
        phone = phone[1:]
    
    if len(phone) != 10:
        return False, ""
    
    if not phone.isdigit():
        return False, ""
    
    operator_code = phone[:3]
    if operator_code not in valid_codes:
        return False, ""
    
    return True, f"+7{phone}"

# ---------------------
# Состояния для FSM
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
# Команда старт
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
# Приём заказа
# ---------------------
@dp.message_handler(lambda m: m.text == "🚕 Такси шақыру")
async def start_order(message: types.Message):
    await OrderStates.waiting_trip_type.set()
    await message.answer(
        "Сапар түрін таңдаңыз:",
        reply_markup=trip_type_kb()
    )

@dp.message_handler(state=OrderStates.waiting_trip_type)
async def get_trip_type(message: types.Message, state: FSMContext):
    if message.text == "🏙 Қала ішінде":
        trip_type = "city"
        trip_type_text = "🏙 Қала ішінде"
    elif message.text == "🌄 Қаладан тыс":
        trip_type = "intercity"
        trip_type_text = "🌄 Қаладан тыс"
    else:
        await message.answer(
            "Сапар түрін таңдаңыз:",
            reply_markup=trip_type_kb()
        )
        return
    
    await state.update_data(trip_type=trip_type, trip_type_text=trip_type_text)
    await OrderStates.waiting_from.set()
    await message.answer(
        "Қай жерден кетесіз? (мекенжайды енгізіңіз)",
        reply_markup=cancel_kb()
    )

@dp.message_handler(state=OrderStates.waiting_from)
async def get_from_addr(message: types.Message, state: FSMContext):
    await state.update_data(from_addr=message.text)
    await OrderStates.waiting_to.set()
    await message.answer(
        "Қайда барасыз? (мекенжайды енгізіңіз)",
        reply_markup=cancel_kb()
    )

@dp.message_handler(state=OrderStates.waiting_to)
async def get_to_addr(message: types.Message, state: FSMContext):
    await state.update_data(to_addr=message.text)
    await OrderStates.waiting_price.set()
    
    data = await state.get_data()
    trip_type = data.get('trip_type', 'city')
    
    if trip_type == 'city':
        price_hint = "Мысал: 500, 700, 1000"
    else:
        price_hint = "Мысал: 2000, 3000, 5000"
    
    await message.answer(
        f"💰 Өзіңіздің баға ұсынысыңызды жазыңыз (теңгемен):\n\n"
        f"{price_hint}\n\n"
        f"⚠️ Жүргізушілер сіздің бағаңызды көреді және қабылдай алады немесе келіспеуі мүмкін.",
        reply_markup=cancel_kb()
    )

@dp.message_handler(state=OrderStates.waiting_price)
async def get_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price < 100:
            await message.answer(
                "❌ Баға тым аз! Кемінде 100 теңге енгізіңіз.",
                reply_markup=cancel_kb()
            )
            return
        if price > 100000:
            await message.answer(
                "❌ Баға тым жоғары! 100,000 теңгеден аспауы керек.",
                reply_markup=cancel_kb()
            )
            return
    except ValueError:
        await message.answer(
            "❌ Қате формат! Тек санды енгізіңіз.\nМысал: 500",
            reply_markup=cancel_kb()
        )
        return
    
    await state.update_data(price=price)
    await OrderStates.waiting_phone.set()
    await message.answer(
        "Телефон нөміріңізді жіберіңіз:\n\n"
        "📱 Қазақстандық нөмір: +7 707/775/701/702/747/705/708/700/776/771/778/706/777\n"
        "Мысал: +7 701 123 45 67 немесе 8 701 123 45 67",
        reply_markup=phone_kb()
    )

@dp.message_handler(content_types=types.ContentType.CONTACT, state=OrderStates.waiting_phone)
async def get_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    is_valid, cleaned_phone = validate_kz_phone(phone)
    
    if not is_valid:
        await message.answer(
            "❌ Қате нөмір!\n\n"
            "Қазақстандық нөмір енгізіңіз:\n"
            "+7 707/775/701/702/747/705/708/700/776/771/778/706/777\n\n"
            "Мысал: +7 701 123 45 67",
            reply_markup=phone_kb()
        )
        return
    
    await process_phone(message, state, cleaned_phone)

@dp.message_handler(state=OrderStates.waiting_phone)
async def get_phone_text(message: types.Message, state: FSMContext):
    phone = message.text
    is_valid, cleaned_phone = validate_kz_phone(phone)
    
    if not is_valid:
        await message.answer(
            "❌ Қате нөмір!\n\n"
            "Қазақстандық нөмір енгізіңіз:\n"
            "+7 707/775/701/702/747/705/708/700/776/771/778/706/777\n\n"
            "Мысал: +7 701 123 45 67 немесе 8 701 123 45 67",
            reply_markup=phone_kb()
        )
        return
    
    await process_phone(message, state, cleaned_phone)

async def process_phone(message: types.Message, state: FSMContext, phone: str):
    data = await state.get_data()
    from_addr = data['from_addr']
    to_addr = data['to_addr']
    price = data['price']
    trip_type = data.get('trip_type', 'city')
    trip_type_text = data.get('trip_type_text', '🏙 Қала ішінде')
    
    order_id = await db.insert_order(
        from_addr, to_addr, price, phone, message.from_user.id, trip_type
    )

    # Отправляем в группу водителей
    msg = await bot.send_message(
        GROUP_ID,
        f"🚕 Жаңа тапсырыс #{order_id}\n"
        f"📌 Түрі: {trip_type_text}\n\n"
        f"📍 Қайдан: {from_addr}\n"
        f"📍 Қайда: {to_addr}\n"
        f"💰 Клиент ұсынысы: {price} ₸\n"
        f"📱 Телефон: {phone}\n\n"
        f"⚠️ Клиент өз бағасын ұсынды. Келіссеңіз - қабылдаңыз!",
        reply_markup=accept_keyboard(order_id)
    )

    await db.update_group_message_id(order_id, msg.message_id)
    await state.finish()
    await message.answer(
        f"✅ Тапсырыс #{order_id} жіберілді!\n\n"
        f"📌 Сапар түрі: {trip_type_text}\n"
        f"💰 Сіздің баға ұсынысыңыз: {price} ₸\n\n"
        f"🚕 Тапсырысыңыз жүргізушілерге жіберілді.\n"
        f"Күтіңіз...",
        reply_markup=main_menu_kb()
    )

# ---------------------
# Принятие заказа
# ---------------------
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("accept_"))
async def callback_accept(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    driver_id = callback.from_user.id
    driver_name = callback.from_user.full_name or callback.from_user.username or "Жүргізуші"

    ok = await db.try_accept_order(order_id, driver_id)
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("Тапсырыс табылмады", show_alert=True)
        return
    
    if not ok:
        await callback.answer("Бұл тапсырысты басқа жүргізуші қабылдап қойды.", show_alert=True)
        return

    await db.register_driver(driver_id, driver_name)

    # Определяем иконку типа поездки
    trip_type_icon = "🏙" if order[9] == "city" else "🌄"
    trip_type_text = "Қала ішінде" if order[9] == "city" else "Қаладан тыс"

    # Обновляем сообщение в группе
    try:
        await bot.edit_message_text(
            chat_id=GROUP_ID,
            message_id=order[8],
            text=f"✅ Тапсырыс #{order_id} қабылданды\n"
                 f"🚗 Жүргізуші: {driver_name}\n"
                 f"📌 Түрі: {trip_type_icon} {trip_type_text}\n\n"
                 f"📍 Қайдан: {order[1]}\n"
                 f"📍 Қайда: {order[2]}\n"
                 f"💰 Бағасы: {order[3]} ₸"
        )
    except Exception as e:
        print("Редактирование сообщения не удалось:", e)

    # Уведомляем водителя
    await bot.send_message(
        driver_id,
        f"✅ Сіз тапсырысты қабылдадыңыз #{order_id}\n"
        f"📌 Түрі: {trip_type_icon} {trip_type_text}\n\n"
        f"📍 Қайдан: {order[1]}\n"
        f"📍 Қайда: {order[2]}\n"
        f"💰 Бағасы: {order[3]} ₸\n"
        f"📱 Клиенттің телефоны: {order[4]}",
        reply_markup=complete_trip_keyboard(order_id)
    )
    
    # Уведомляем пассажира
    passenger_id = order[5]
    await bot.send_message(
        passenger_id,
        f"✅ Жүргізуші табылды!\n"
        f"🚗 {driver_name}\n"
        f"💰 Баға: {order[3]} ₸\n\n"
        f"Жүргізуші жолда..."
    )

    await callback.answer("Тапсырыс қабылданды!")

# ---------------------
# Завершение поездки
# ---------------------
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("complete_"))
async def callback_complete(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("Тапсырыс табылмады", show_alert=True)
        return

    passenger_id = order[5]
    await db.complete_order(order_id)

    await callback.message.answer("✅ Сапар аяқталды! Рахмет!")
    await callback.answer("Сапар аяқталды!")

    # Просим пассажира оценить поездку
    await bot.send_message(
        passenger_id,
        f"✅ Сіздің сапарыңыз аяқталды!\n"
        "Жүргізушіні бағалаңыз:",
        reply_markup=rating_keyboard(order_id)
    )

# ---------------------
# Оценка водителя
# ---------------------
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("rate_"))
async def callback_rate(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    order_id = int(parts[1])
    rating = int(parts[2])

    await db.set_rating(order_id, rating)
    
    try:
        await callback.message.edit_text(
            f"⭐ Рахмет! Сіз жүргізушіні {rating} ⭐ деп бағаладыңыз."
        )
    except:
        await callback.message.answer(
            f"⭐ Рахмет! Сіз жүргізушіні {rating} ⭐ деп бағаладыңыз."
        )
    
    await callback.answer("Рахмет за бағалауды!")

# ---------------------
# Мои заказы (опционально)
# ---------------------
@dp.message_handler(lambda m: m.text == "📊 Менің тапсырыстарым")
async def my_orders(message: types.Message):
    await message.answer("Бұл функция әзірше жасалуда...")

# ---------------------
# Запуск
# ---------------------
# ---------------------
# Запуск
# ---------------------
if __name__ == '__main__':
    import os
    from aiohttp import web
    
    # Получаем URL вебхука из Render
    WEBHOOK_HOST = os.getenv('RENDER_EXTERNAL_URL', 'https://lenger-taxi24-bot.onrender.com')
    WEBHOOK_PATH = f'/webhook/{os.getenv("BOT_TOKEN").split(":")[1]}'
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
    
    # Порт для веб-сервера
    WEBAPP_HOST = '0.0.0.0'
    WEBAPP_PORT = int(os.getenv('PORT', 10000))
    
    async def on_startup(app):
        # Инициализируем базу данных
        await db.init_db()
        
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        print(f'Webhook set to {WEBHOOK_URL}')
    
    async def on_startup(app):
        await bot.delete_webhook()
    
    async def webhook_handle(request):
        update = await request.json()
        telegram_update = types.Update(**update)
        
        # Устанавливаем текущий диспетчер
        Dispatcher.set_current(dp)
        Bot.set_current(bot)
        
        await dp.process_update(telegram_update)
        return web.Response()
    
    # Создаем веб-приложение
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, webhook_handle)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    # Запускаем веб-сервер
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)