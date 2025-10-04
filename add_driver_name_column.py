import sqlite3
conn = sqlite3.connect("taxi.db")
cur = conn.cursor()
# проверим есть ли колонка driver_name
cur.execute("PRAGMA table_info(orders)")
cols = [r[1] for r in cur.fetchall()]
if "driver_name" not in cols:
    cur.execute("ALTER TABLE orders ADD COLUMN driver_name TEXT")
    conn.commit()
    print("Добавил колонку driver_name")
else:
    print("Колонка driver_name уже есть")
conn.close()
