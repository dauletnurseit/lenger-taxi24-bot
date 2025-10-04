# stats.py — консольная статистика
import sqlite3

DB_PATH = "taxi.db"
DRIVER_PERCENT = 0.8  # 80% водителю; поменяй при необходимости

def show_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(driver_name, CAST(driver_id AS TEXT)) as driver,
               COUNT(*) as cnt,
               COALESCE(SUM(price),0) as total
        FROM orders
        WHERE status='accepted'
        GROUP BY driver
        ORDER BY total DESC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("Нет принятых заказов для расчёта.")
        return

    print("Статистика по водителям:\n")
    for driver, cnt, total in rows:
        driver_share = int(total * DRIVER_PERCENT)
        service_share = int(total - driver_share)
        print(f"{driver}: {cnt} заказ(ов), всего {total} ₸")
        print(f"  → Водителю: {driver_share} ₸")
        print(f"  → Сервису:  {service_share} ₸\n")

if __name__ == "__main__":
    show_stats()
