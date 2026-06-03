import sqlite3
import json
import os
from datetime import datetime

# المسار بتاع قاعدة البيانات - هتتخزن جنب الملفات
DB_PATH = os.path.join(os.path.dirname(__file__), "car_expert.db")
def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """إنشاء الجداول المطلوبة"""
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الحجوزات
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
    
    # جدول محادثات الشات
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
    
    # جدول سيارات المستخدمين
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
    
    conn.commit()
    conn.close()
    print(f"✅ قاعدة البيانات جاهزة في: {DB_PATH}")

def save_user(name, email, phone, password):
    """حفظ مستخدم جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, phone, password) VALUES (?, ?, ?, ?)",
            (name, email, phone, password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "البريد الإلكتروني مستخدم بالفعل"}

def get_user(email, password):
    """جلب مستخدم بواسطة البريد وكلمة المرور"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, password)
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    """جلب مستخدم بواسطة ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def save_booking(user_id, service, name, phone, location, date_time, car_details):
    """حفظ حجز جديد"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookings (user_id, service, name, phone, location, date_time, car_details) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, service, name, phone, location, date_time, car_details)
    )
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return booking_id

def get_user_bookings(user_id):
    """جلب حجوزات المستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    bookings = cursor.fetchall()
    conn.close()
    return [dict(booking) for booking in bookings]

def delete_booking(booking_id, user_id):
    """حذف حجز"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM bookings WHERE id = ? AND user_id = ?",
        (booking_id, user_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def save_chat_message(user_id, message, response, image=None):
    """حفظ محادثة الشات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (user_id, message, response, image) VALUES (?, ?, ?, ?)",
        (user_id, message, response, image)
    )
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=50):
    """جلب تاريخ المحادثات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    history = cursor.fetchall()
    conn.close()
    return [dict(h) for h in history]

def clear_chat_history(user_id):
    """مسح تاريخ المحادثات لمستخدم معين"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected

def save_user_car(user_id, car_make, car_model, car_year, car_engine):
    """حفظ معلومات سيارة المستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # حذف السجل القديم إن وجد
    cursor.execute("DELETE FROM user_cars WHERE user_id = ?", (user_id,))
    cursor.execute(
        "INSERT INTO user_cars (user_id, car_make, car_model, car_year, car_engine) VALUES (?, ?, ?, ?, ?)",
        (user_id, car_make, car_model, car_year, car_engine)
    )
    conn.commit()
    conn.close()
    return True

def get_user_car(user_id):
    """جلب معلومات سيارة المستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_cars WHERE user_id = ?", (user_id,))
    car = cursor.fetchone()
    conn.close()
    return dict(car) if car else None

# تهيئة قاعدة البيانات عند التشغيل
init_db()