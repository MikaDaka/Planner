import sqlite3
import os
import sys

DB_NAME = 'planner.db'

def get_db_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), DB_NAME)
    return DB_NAME

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline DATE,
            priority TEXT CHECK(priority IN ('low','medium','high')) DEFAULT 'medium',
            category TEXT,
            status TEXT CHECK(status IN ('pending','in progress','completed','postponed')) DEFAULT 'pending',
            tags TEXT,
            recurrence TEXT,
            reminder DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_task(task_data):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (title, description, deadline, priority, category, status, tags, recurrence, reminder)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        task_data['title'],
        task_data.get('description', ''),
        task_data.get('deadline'),
        task_data.get('priority', 'medium'),
        task_data.get('category', ''),
        task_data.get('status', 'pending'),
        task_data.get('tags', ''),
        task_data.get('recurrence'),
        task_data.get('reminder')
    ))
    conn.commit()
    conn.close()

def get_all_tasks_ordered():
    # high → medium → low, затем по дате создания
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM tasks
        ORDER BY
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            created_at DESC
    """)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_all_tasks():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_tasks_by_category(category):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE category = ? ORDER BY created_at DESC", (category,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_tasks_by_status(status):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_tasks_by_deadline(start_date=None, end_date=None):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if start_date:
        query += " AND deadline >= ?"
        params.append(start_date)
    if end_date:
        query += " AND deadline <= ?"
        params.append(end_date)
    query += " ORDER BY deadline ASC"
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, new_status):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def search_tasks(keyword):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM tasks 
        WHERE title LIKE ? OR description LIKE ? OR category LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
    tasks = cursor.fetchall()
    conn.close()
    return tasks


