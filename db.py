import aiosqlite

DB_PATH = "taxi.db"
db_conn: aiosqlite.Connection | None = None  # глобальное соединение


# ---------------------
# Инициализация базы
# ---------------------
async def init_db(path: str = DB_PATH):
    global db_conn
    db_conn = await aiosqlite.connect(path)

    # Создаём таблицу orders
    await db_conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_addr TEXT,
            to_addr TEXT,
            price INTEGER,
            phone TEXT,
            passenger_id INTEGER,
            status TEXT DEFAULT 'new',
            driver_id INTEGER,
            group_message_id INTEGER,
            trip_type TEXT DEFAULT 'city',
            completed INTEGER DEFAULT 0,
            rating INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Создаём таблицу drivers
    await db_conn.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            car_model TEXT,
            rating REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0
        )
    """)

    # Проверяем и добавляем новые колонки (миграция)
    try:
        cursor = await db_conn.execute("PRAGMA table_info(orders)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Добавляем completed если нет
        if 'completed' not in column_names:
            print("Добавляем колонку 'completed'...")
            await db_conn.execute("ALTER TABLE orders ADD COLUMN completed INTEGER DEFAULT 0")
            print("Колонка 'completed' добавлена!")

        # Добавляем trip_type если нет
        if 'trip_type' not in column_names:
            print("Добавляем колонку 'trip_type'...")
            await db_conn.execute("ALTER TABLE orders ADD COLUMN trip_type TEXT DEFAULT 'city'")
            print("Колонка 'trip_type' добавлена!")

        # Добавляем rating если нет
        if 'rating' not in column_names:
            print("Добавляем колонку 'rating'...")
            await db_conn.execute("ALTER TABLE orders ADD COLUMN rating INTEGER DEFAULT 0")
            print("Колонка 'rating' добавлена!")

        await cursor.close()
    except Exception as e:
        print(f"Ошибка при миграции: {e}")

    await db_conn.commit()
    print("База данных инициализирована!")


# ---------------------
# Функции работы с БД
# ---------------------
async def insert_order(from_addr, to_addr, price, phone, passenger_id, trip_type='city'):
    cur = await db_conn.execute(
        "INSERT INTO orders (from_addr,to_addr,price,phone,passenger_id,trip_type) VALUES (?,?,?,?,?,?)",
        (from_addr, to_addr, price, phone, passenger_id, trip_type)
    )
    await db_conn.commit()
    last_id = cur.lastrowid
    await cur.close()
    return last_id


async def update_group_message_id(order_id, message_id):
    await db_conn.execute(
        "UPDATE orders SET group_message_id=? WHERE id=?",
        (message_id, order_id)
    )
    await db_conn.commit()


async def get_order(order_id):
    cur = await db_conn.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def try_accept_order(order_id, driver_id):
    await db_conn.execute(
        "UPDATE orders SET status='accepted', driver_id=? WHERE id=? AND status='new'",
        (driver_id, order_id)
    )
    await db_conn.commit()

    cur = await db_conn.execute("SELECT driver_id FROM orders WHERE id=?", (order_id,))
    row = await cur.fetchone()
    await cur.close()
    return bool(row and row[0] == driver_id)


async def complete_order(order_id):
    await db_conn.execute("UPDATE orders SET completed=1 WHERE id=?", (order_id,))
    await db_conn.commit()


async def set_rating(order_id, rating: int):
    # Сохраняем рейтинг в заказе
    await db_conn.execute("UPDATE orders SET rating=? WHERE id=?", (rating, order_id))
    await db_conn.commit()
    
    # Обновляем средний рейтинг водителя
    cur = await db_conn.execute("SELECT driver_id FROM orders WHERE id=?", (order_id,))
    row = await cur.fetchone()
    await cur.close()
    if row and row[0]:
        driver_id = row[0]
        await rate_driver(driver_id, rating)


async def rate_driver(driver_id: int, new_rating: float):
    cur = await db_conn.execute("SELECT rating, rating_count FROM drivers WHERE id=?", (driver_id,))
    row = await cur.fetchone()
    await cur.close()

    if row:
        old_rating, rating_count = row
        total_score = old_rating * rating_count + new_rating
        new_count = rating_count + 1
        new_avg = total_score / new_count
        await db_conn.execute(
            "UPDATE drivers SET rating=?, rating_count=? WHERE id=?",
            (new_avg, new_count, driver_id)
        )
    else:
        await db_conn.execute(
            "INSERT INTO drivers (id, rating, rating_count) VALUES (?, ?, ?)",
            (driver_id, new_rating, 1)
        )
    await db_conn.commit()


async def register_driver(driver_id: int, name: str = None):
    cur = await db_conn.execute("SELECT id FROM drivers WHERE id=?", (driver_id,))
    row = await cur.fetchone()
    await cur.close()

    if not row:
        await db_conn.execute(
            "INSERT INTO drivers (id, name) VALUES (?, ?)",
            (driver_id, name)
        )
        await db_conn.commit()


# ---------------------
# Новые функции для истории заказов
# ---------------------
async def get_driver(driver_id: int):
    """Получить информацию о водителе"""
    cur = await db_conn.execute("SELECT * FROM drivers WHERE id=?", (driver_id,))
    row = await cur.fetchone()
    await cur.close()
    return row


async def get_driver_orders(driver_id: int):
    """Получить все заказы водителя (сортировка по дате, новые первые)"""
    cur = await db_conn.execute(
        "SELECT * FROM orders WHERE driver_id=? ORDER BY created_at DESC",
        (driver_id,)
    )
    rows = await cur.fetchall()
    await cur.close()
    return rows