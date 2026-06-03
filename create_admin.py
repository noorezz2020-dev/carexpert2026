import sqlite3

def create_admin():
    conn = sqlite3.connect("car_expert.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (name, email, phone, password) 
            VALUES ('Admin', 'admin@carexpert.com', '01000000000', 'admin123')
        """)
        conn.commit()
        print("✅ تم إنشاء حساب المدير بنجاح!")
        print("📧 البريد: admin@carexpert.com")
        print("🔑 كلمة المرور: admin123")
    except sqlite3.IntegrityError:
        print("⚠️ حساب المدير موجود بالفعل!")
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin()