from flask import Flask, render_template_string, request
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB_PATH = "taxi.db"
DRIVER_PERCENT = 0.80  # 80% водителю
SERVICE_PERCENT = 0.20  # 20% сервису

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lenger Taxi24 - Админ панель</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        .filters-panel {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .filters-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        .filter-group {
            display: flex;
            flex-direction: column;
        }
        .filter-group label {
            font-weight: 600;
            color: #666;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        .filter-group input,
        .filter-group select {
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        .filter-group input:focus,
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #5a6268;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card h3 {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .stat-card .value {
            color: #667eea;
            font-size: 2.5em;
            font-weight: bold;
        }
        .stat-card .label {
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .data-table {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
            margin-bottom: 30px;
        }
        .table-header {
            background: #667eea;
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .table-header h2 {
            font-size: 1.5em;
        }
        .table-container {
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #666;
            border-bottom: 2px solid #e0e0e0;
            white-space: nowrap;
        }
        td {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        tr:hover {
            background: #f8f9ff;
        }
        .driver-name {
            font-weight: 600;
            color: #333;
        }
        .rating {
            color: #ffa500;
            font-size: 1.1em;
        }
        .money {
            color: #28a745;
            font-weight: 600;
        }
        .service-money {
            color: #667eea;
            font-weight: 600;
        }
        .phone {
            color: #17a2b8;
            font-weight: 500;
        }
        .status-new {
            background: #ffc107;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            white-space: nowrap;
        }
        .status-accepted {
            background: #28a745;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            white-space: nowrap;
        }
        .status-completed {
            background: #6c757d;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            white-space: nowrap;
        }
        .no-data {
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 1.1em;
        }
        .driver-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .driver-link:hover {
            text-decoration: underline;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 12px 25px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
            color: #666;
        }
        .tab.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .tab:hover {
            border-color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚕 Lenger Taxi24</h1>
            <p>Админ панель - Статистика и управление</p>
        </div>

        <div class="filters-panel">
            <form method="GET" action="/">
                <div class="filters-grid">
                    <div class="filter-group">
                        <label>От даты:</label>
                        <input type="date" name="date_from" value="{{ date_from }}">
                    </div>
                    <div class="filter-group">
                        <label>До даты:</label>
                        <input type="date" name="date_to" value="{{ date_to }}">
                    </div>
                    <div class="filter-group">
                        <label>Водитель:</label>
                        <select name="driver_id">
                            <option value="">Все водители</option>
                            {% for driver in all_drivers %}
                            <option value="{{ driver.id }}" {% if driver.id|string == selected_driver %}selected{% endif %}>
                                {{ driver.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Статус:</label>
                        <select name="status">
                            <option value="" {% if not selected_status %}selected{% endif %}>Все</option>
                            <option value="new" {% if selected_status == 'new' %}selected{% endif %}>Новые</option>
                            <option value="accepted" {% if selected_status == 'accepted' %}selected{% endif %}>В работе</option>
                            <option value="completed" {% if selected_status == 'completed' %}selected{% endif %}>Завершенные</option>
                        </select>
                    </div>
                </div>
                <div class="filter-buttons">
                    <button type="submit" class="btn btn-primary">🔍 Применить фильтры</button>
                    <a href="/" class="btn btn-secondary">🔄 Сбросить</a>
                    <button type="button" onclick="setToday()" class="btn btn-success">📅 Сегодня</button>
                    <button type="button" onclick="setWeek()" class="btn btn-success">📅 Неделя</button>
                    <button type="button" onclick="setMonth()" class="btn btn-success">📅 Месяц</button>
                </div>
            </form>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Всего заказов</h3>
                <div class="value">{{ stats.total_orders }}</div>
                <div class="label">За выбранный период</div>
            </div>
            <div class="stat-card">
                <h3>Выполнено</h3>
                <div class="value">{{ stats.completed_orders }}</div>
                <div class="label">Завершённых поездок</div>
            </div>
            <div class="stat-card">
                <h3>Общий доход</h3>
                <div class="value">{{ stats.total_revenue }} ₸</div>
                <div class="label">Сумма всех заказов</div>
            </div>
            <div class="stat-card">
                <h3>Доход водителей (80%)</h3>
                <div class="value">{{ stats.driver_revenue }} ₸</div>
                <div class="label">Выплаты водителям</div>
            </div>
            <div class="stat-card">
                <h3>Доход сервиса (20%)</h3>
                <div class="value">{{ stats.service_revenue }} ₸</div>
                <div class="label">Комиссия сервиса</div>
            </div>
        </div>

        {% if show_driver_detail %}
        <div class="data-table">
            <div class="table-header">
                <h2>👤 Детальный отчет: {{ driver_detail.name }}</h2>
                <a href="/" class="btn btn-secondary">← Назад</a>
            </div>
            <div style="padding: 20px;">
                <div class="stats-grid" style="margin-bottom: 20px;">
                    <div class="stat-card">
                        <h3>Всего заказов</h3>
                        <div class="value">{{ driver_detail.total_orders }}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Выполнено</h3>
                        <div class="value">{{ driver_detail.completed_orders }}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Рейтинг</h3>
                        <div class="value rating">⭐ {{ driver_detail.rating }}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Заработано</h3>
                        <div class="value money">{{ driver_detail.driver_share }} ₸</div>
                        <div class="label">Из {{ driver_detail.total_sum }} ₸</div>
                    </div>
                </div>
            </div>
        </div>
        {% else %}
        <div class="data-table">
            <div class="table-header">
                <h2>📊 Статистика по водителям</h2>
            </div>
            {% if drivers %}
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Водитель</th>
                            <th>Рейтинг</th>
                            <th>Заказов</th>
                            <th>Выполнено</th>
                            <th>Общая сумма</th>
                            <th>Доля водителя (80%)</th>
                            <th>Доля сервиса (20%)</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for driver in drivers %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td class="driver-name">{{ driver.name }}</td>
                            <td class="rating">⭐ {{ driver.rating }}</td>
                            <td>{{ driver.total_orders }}</td>
                            <td>{{ driver.completed_orders }}</td>
                            <td class="money">{{ driver.total_sum }} ₸</td>
                            <td class="money">{{ driver.driver_share }} ₸</td>
                            <td class="service-money">{{ driver.service_share }} ₸</td>
                            <td>
                                <a href="/?driver_id={{ driver.id }}&date_from={{ date_from }}&date_to={{ date_to }}&view=detail" 
                                   class="driver-link">Детали →</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="no-data">Нет данных по водителям</div>
            {% endif %}
        </div>
        {% endif %}

        <div class="data-table">
            <div class="table-header">
                <h2>📋 Заказы за период</h2>
                <span>Всего: {{ orders|length }}</span>
            </div>
            {% if orders %}
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Дата/Время</th>
                            <th>Откуда</th>
                            <th>Куда</th>
                            <th>Цена</th>
                            <th>Телефон клиента</th>
                            <th>Водитель</th>
                            <th>Статус</th>
                            <th>Оценка</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for order in orders %}
                        <tr>
                            <td>#{{ order.id }}</td>
                            <td>{{ order.created_at }}</td>
                            <td>{{ order.from_addr }}</td>
                            <td>{{ order.to_addr }}</td>
                            <td class="money">{{ order.price }} ₸</td>
                            <td class="phone">{{ order.phone }}</td>
                            <td>{{ order.driver_name or '—' }}</td>
                            <td>
                                {% if order.completed == 1 %}
                                    <span class="status-completed">Завершён</span>
                                {% elif order.status == 'accepted' %}
                                    <span class="status-accepted">В работе</span>
                                {% else %}
                                    <span class="status-new">Новый</span>
                                {% endif %}
                            </td>
                            <td class="rating">
                                {% if order.rating %}
                                    {{ order.rating }} ⭐
                                {% else %}
                                    —
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="no-data">Нет заказов за выбранный период</div>
            {% endif %}
        </div>
    </div>

    <script>
        function setToday() {
            const today = new Date().toISOString().split('T')[0];
            document.querySelector('input[name="date_from"]').value = today;
            document.querySelector('input[name="date_to"]').value = today;
            document.querySelector('form').submit();
        }

        function setWeek() {
            const today = new Date();
            const weekAgo = new Date(today);
            weekAgo.setDate(today.getDate() - 7);
            document.querySelector('input[name="date_from"]').value = weekAgo.toISOString().split('T')[0];
            document.querySelector('input[name="date_to"]').value = today.toISOString().split('T')[0];
            document.querySelector('form').submit();
        }

        function setMonth() {
            const today = new Date();
            const monthAgo = new Date(today);
            monthAgo.setMonth(today.getMonth() - 1);
            document.querySelector('input[name="date_from"]').value = monthAgo.toISOString().split('T')[0];
            document.querySelector('input[name="date_to"]').value = today.toISOString().split('T')[0];
            document.querySelector('form').submit();
        }
    </script>
</body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    conn = get_db_connection()
    
    # Получаем параметры фильтрации
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    selected_driver = request.args.get('driver_id', '')
    selected_status = request.args.get('status', '')
    view_mode = request.args.get('view', '')
    
    # Если даты не указаны, берем последний месяц
    if not date_from and not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Строим WHERE условие для фильтрации
    where_conditions = []
    params = []
    
    if date_from:
        where_conditions.append("DATE(o.created_at) >= ?")
        params.append(date_from)
    
    if date_to:
        where_conditions.append("DATE(o.created_at) <= ?")
        params.append(date_to)
    
    if selected_driver:
        where_conditions.append("o.driver_id = ?")
        params.append(selected_driver)
    
    if selected_status == 'new':
        where_conditions.append("o.status = 'new'")
    elif selected_status == 'accepted':
        where_conditions.append("o.status = 'accepted' AND o.completed = 0")
    elif selected_status == 'completed':
        where_conditions.append("o.completed = 1")
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Получаем всех водителей для селекта
    all_drivers = conn.execute("SELECT id, name FROM drivers ORDER BY name").fetchall()
    
    # Общая статистика за период
    stats_query = f"""
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_orders,
            COALESCE(SUM(CASE WHEN status = 'accepted' OR completed = 1 THEN price ELSE 0 END), 0) as total_revenue
        FROM orders o
        {where_clause}
    """
    stats_row = conn.execute(stats_query, params).fetchone()
    
    total_revenue = stats_row['total_revenue']
    driver_revenue = int(total_revenue * DRIVER_PERCENT)
    service_revenue = int(total_revenue * SERVICE_PERCENT)
    
    stats = {
        'total_orders': stats_row['total_orders'],
        'completed_orders': stats_row['completed_orders'],
        'total_revenue': total_revenue,
        'driver_revenue': driver_revenue,
        'service_revenue': service_revenue
    }
    
    # Детальный отчет по водителю
    show_driver_detail = False
    driver_detail = None
    
    if view_mode == 'detail' and selected_driver:
        show_driver_detail = True
        driver_query = f"""
            SELECT 
                d.name,
                d.rating,
                COUNT(o.id) as total_orders,
                SUM(CASE WHEN o.completed = 1 THEN 1 ELSE 0 END) as completed_orders,
                COALESCE(SUM(CASE WHEN o.status = 'accepted' OR o.completed = 1 THEN o.price ELSE 0 END), 0) as total_sum
            FROM drivers d
            LEFT JOIN orders o ON d.id = o.driver_id
            WHERE d.id = ?
        """
        detail_params = [selected_driver]
        
        if date_from:
            driver_query += " AND DATE(o.created_at) >= ?"
            detail_params.append(date_from)
        if date_to:
            driver_query += " AND DATE(o.created_at) <= ?"
            detail_params.append(date_to)
        
        driver_query += " GROUP BY d.id, d.name, d.rating"
        
        driver_row = conn.execute(driver_query, detail_params).fetchone()
        
        if driver_row:
            total_sum = driver_row['total_sum']
            driver_detail = {
                'name': driver_row['name'],
                'rating': f"{driver_row['rating']:.1f}" if driver_row['rating'] else 'N/A',
                'total_orders': driver_row['total_orders'],
                'completed_orders': driver_row['completed_orders'],
                'total_sum': total_sum,
                'driver_share': int(total_sum * DRIVER_PERCENT),
                'service_share': int(total_sum * SERVICE_PERCENT)
            }
    
    # Статистика по водителям
    drivers_query = f"""
        SELECT 
            d.id,
            d.name,
            d.rating,
            COUNT(o.id) as total_orders,
            SUM(CASE WHEN o.completed = 1 THEN 1 ELSE 0 END) as completed_orders,
            COALESCE(SUM(CASE WHEN o.status = 'accepted' OR o.completed = 1 THEN o.price ELSE 0 END), 0) as total_sum
        FROM drivers d
        LEFT JOIN orders o ON d.id = o.driver_id
    """
    
    if where_conditions:
        # Убираем условие по driver_id из where_conditions для общего списка водителей
        driver_where = [c for c in where_conditions if 'driver_id' not in c]
        driver_params = [p for i, p in enumerate(params) if i < len(driver_where)]
        if driver_where:
            drivers_query += " WHERE " + " AND ".join(driver_where)
            drivers_data = conn.execute(drivers_query + " GROUP BY d.id ORDER BY total_sum DESC", driver_params).fetchall()
        else:
            drivers_data = conn.execute(drivers_query + " GROUP BY d.id ORDER BY total_sum DESC").fetchall()
    else:
        drivers_data = conn.execute(drivers_query + " GROUP BY d.id ORDER BY total_sum DESC").fetchall()
    
    drivers = []
    for row in drivers_data:
        total_sum = row['total_sum']
        drivers.append({
            'id': row['id'],
            'name': row['name'] or 'Неизвестно',
            'rating': f"{row['rating']:.1f}" if row['rating'] else 'N/A',
            'total_orders': row['total_orders'],
            'completed_orders': row['completed_orders'],
            'total_sum': total_sum,
            'driver_share': int(total_sum * DRIVER_PERCENT),
            'service_share': int(total_sum * SERVICE_PERCENT)
        })
    
    # Заказы за период
    orders_query = f"""
        SELECT 
            o.*,
            d.name as driver_name
        FROM orders o
        LEFT JOIN drivers d ON o.driver_id = d.id
        {where_clause}
        ORDER BY o.created_at DESC
    """
    orders = conn.execute(orders_query, params).fetchall()
    
    conn.close()
    
    return render_template_string(
        HTML_TEMPLATE,
        date_from=date_from,
        date_to=date_to,
        selected_driver=selected_driver,
        selected_status=selected_status,
        all_drivers=all_drivers,
        stats=stats,
        drivers=drivers,
        orders=orders,
        show_driver_detail=show_driver_detail,
        driver_detail=driver_detail
    )

if __name__ == '__main__':
    print("🚀 Запуск админ-панели...")
    print("📊 Откройте в браузере: http://localhost:5000")
    print("⚠️  Для остановки нажмите Ctrl+C")
    app.run(debug=True, host='0.0.0.0', port=5000)