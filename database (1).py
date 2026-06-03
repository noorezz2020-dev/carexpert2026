import sqlite3
import json
import os
from datetime import datetime

DB_PATH = r"D:\CarExpertProject\car_expert.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            profile_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            date_time TEXT NOT NULL,
            car_details TEXT,
            status TEXT DEFAULT 'جديد',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            car_make TEXT,
            car_model TEXT,
            car_year TEXT,
            car_engine TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_services INTEGER DEFAULT 0,
            active_teams INTEGER DEFAULT 4,
            avg_response_time INTEGER DEFAULT 15,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM system_stats")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO system_stats (total_services, active_teams, avg_response_time) VALUES (128, 4, 15)")
    
    conn.commit()
    conn.close()
    print(f"✅ قاعدة البيانات جاهزة")

def save_user(name, email, phone, password, is_admin=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (name, email, phone, password, is_admin) VALUES (?, ?, ?, ?, ?)",
                       (name, email, phone, password, is_admin))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "البريد الإلكتروني مستخدم بالفعل"}

def get_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_profile(user_id, name, email, phone, profile_image=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if profile_image:
        cursor.execute("UPDATE users SET name = ?, email = ?, phone = ?, profile_image = ? WHERE id = ?",
                       (name, email, phone, profile_image, user_id))
    else:
        cursor.execute("UPDATE users SET name = ?, email = ?, phone = ? WHERE id = ?",
                       (name, email, phone, user_id))
    conn.commit()
    conn.close()
    return True

def save_booking(user_id, service, name, phone, location, date_time, car_details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (user_id, service, name, phone, location, date_time, car_details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (user_id, service, name, phone, location, date_time, car_details))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id

def get_user_bookings(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    return [dict(b) for b in bookings]

def delete_booking(booking_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ? AND user_id = ?", (booking_id, user_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def save_chat_message(user_id, message, response, image=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_id, message, response, image) VALUES (?, ?, ?, ?)",
                   (user_id, message, response, image))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    history = cursor.fetchall()
    conn.close()
    return [dict(h) for h in history]

def clear_chat_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected

def save_user_car(user_id, car_make, car_model, car_year, car_engine):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_cars WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT INTO user_cars (user_id, car_make, car_model, car_year, car_engine) VALUES (?, ?, ?, ?, ?)",
                   (user_id, car_make, car_model, car_year, car_engine))
    conn.commit()
    conn.close()
    return True

def get_user_car(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_cars WHERE user_id = ?", (user_id,))
    car = cursor.fetchone()
    conn.close()
    return dict(car) if car else None

def get_system_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_services, active_teams, avg_response_time FROM system_stats ORDER BY id DESC LIMIT 1")
    stats = cursor.fetchone()
    conn.close()
    return dict(stats) if stats else {"total_services": 128, "active_teams": 4, "avg_response_time": 15}

def update_system_stats(total_services, active_teams, avg_response_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO system_stats (total_services, active_teams, avg_response_time, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                   (total_services, active_teams, avg_response_time))
    conn.commit()
    conn.close()
    return True

def create_admin_user():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = ?", ("ramzyh74@gmail.com",))
    cursor.execute("INSERT INTO users (name, email, phone, password, is_admin) VALUES (?, ?, ?, ?, ?)",
                   ("Ramzy Admin", "ramzyh74@gmail.com", "01000000000", "123456789", 1))
    conn.commit()
    conn.close()
    print("✅ تم إنشاء حساب المدير بنجاح!")

init_db()
create_admin_user()