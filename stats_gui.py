import sqlite3
import tkinter as tk
from tkinter import ttk

DB_PATH = r"C:\Users\Daulet\Desktop\LENGER TAXI24 BOT\taxi.db"

def load_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, from_addr, to_addr, price, phone, status, driver_id, created_at FROM orders")
    rows = cur.fetchall()
    conn.close()
    return rows

def refresh_table():
    # очистка
    for row in tree.get_children():
        tree.delete(row)
    # загрузка новых данных
    for row in load_data():
        tree.insert("", tk.END, values=row)

root = tk.Tk()
root.title("Статистика заказов такси")

# таблица
columns = ("ID", "Откуда", "Куда", "Цена", "Телефон", "Статус", "ID водителя", "Создано")
tree = ttk.Treeview(root, columns=columns, show="headings")

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=120)

tree.pack(fill=tk.BOTH, expand=True)

# кнопка обновления
btn_refresh = tk.Button(root, text="🔄 Обновить", command=refresh_table)
btn_refresh.pack(pady=5)

# загрузка при старте
refresh_table()

root.mainloop()
