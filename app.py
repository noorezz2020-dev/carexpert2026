from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import re
import base64
import os
import random
from PIL import Image
import io
from datetime import datetime
from image_editor import change_car_color, add_accessory_to_car
from database import (
    save_user, get_user, get_user_by_id,
    save_booking, get_user_bookings, delete_booking,
    save_chat_message, get_chat_history, clear_chat_history,
    get_db_connection, save_user_car, get_user_car
)

app = FastAPI()

# إنشاء المجلدات
for folder in ["static", "uploads"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "AIzaSyB1qRyMVMsvV2nlDyYb2bmnBjiq7lMXGRc"

# استخدام Gemini
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=API_KEY)
    GEMINI_AVAILABLE = True
    print("✅ Google Gemini is available and working")
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google GenAI not installed. Run: pip install google-genai")
except Exception as e:
    GEMINI_AVAILABLE = False
    print(f"⚠️ Gemini error: {e}")

# تخزين مؤقت للمحادثات (لكل مستخدم)
user_conversations = {}

SERVICES = {
    "فحص متنقل": "فحص السيارة في موقع العميل",
    "فحص سيارات مستعملة": "فحص شامل قبل شراء سيارة مستعملة",
    "غسيل احترافي": "غسيل السيارات بأحدث التقنيات",
    "إكسسوارات": "تركيب اكسسوارات السيارات",
    "تأجير": "تأجير السيارات لشركات السياحة",
    "حجز صيانة": "حجز موعد صيانة السيارة",
    "صيانة دورية": "تغيير الزيت أو الإطارات دورياً",
    "خدمات متنقلة": "تبديل البطاريات أو تصليح الإطارات"
}

def diagnose_with_gemini(problem, image_base64=None, user_name="عميل", user_id=None, car_info=None, conversation_history=None):
    """تحليل المشكلة مع سياق المحادثة ومعلومات السيارة"""
    
    # بناء سياق المحادثة
    context = ""
    if conversation_history:
        recent = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
        context = "\n".join(recent)
        context = f"\n\nسجل المحادثة السابقة:\n{context}\n"
    
    # معلومات السيارة
    car_context = ""
    if car_info and car_info.get("car_make"):
        car_context = f"\n\nمعلومات سيارة {user_name}:\n- الماركة: {car_info.get('car_make', 'غير معروف')}\n- الموديل: {car_info.get('car_model', 'غير معروف')}\n- السنة: {car_info.get('car_year', 'غير معروف')}\n"
    
    if not GEMINI_AVAILABLE:
        return f"⚠️ عذراً يا {user_name}، خدمة الذكاء الاصطناعي غير متاحة حالياً.\n\n[SERVICE_SUGGESTION] فحص متنقل"
    
    try:
        contents = []
        
        # التحقق إذا كان البوت بيسأل عن نوع العربية
        ask_for_car = ""
        if not car_info or not car_info.get("car_make"):
            ask_for_car = "\n\nملاحظة مهمة: لو المستخدم لسه مدخلش نوع عربيته، اسأله: 'إيه نوع عربيتك عشان أقدر أساعدك أحسن؟'"
        
        system_prompt = f"""أنت خبير سيارات ودود وذكي اسمك "كار إكسبيرت". اتكلم مع {user_name} زي صاحبك.

قواعد مهمة جداً:
1. افتكر الكلام اللي فات بينك وبين المستخدم (السياق تحت)
2. لو المستخدم اتكلم عن مشكلة قبل كده، كمل عليها ومتكررش التحية
3. متقولش "أهلاً" أو "ازيك" في كل مرة، كمل الكلام عادي
4. لو معرفش نوع عربيته، اسأله سؤال واحد بس: "إيه نوع عربيتك عشان أقدر أساعدك أحسن؟"
5. خلي كلامك طبيعي، بسيط، بالعامية المصرية
6. استخدم رموز تعبيرية بشكل بسيط
{ask_for_car}
{car_context}
{context}

المستخدم قال دلوقتي: {problem}

رد عليا دلوقتي كأننا بنكمل كلام:"""
        contents.append(system_prompt)
        
        # إضافة الصورة
        if image_base64:
            try:
                image_bytes = base64.b64decode(image_base64)
                image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                contents.append(image_part)
            except:
                pass
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents
        )
        
        return response.text
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ خطأ في Gemini: {error_msg}")
        
        if "503" in error_msg or "high demand" in error_msg:
            return f"آسف يا {user_name}، فيه ضغط عالي على السيرفرات دلوقتي. جرب تاني بعد دقيقة 🙏\n\n[SERVICE_SUGGESTION] فحص متنقل"
        elif "429" in error_msg:
            return f"آسف يا {user_name}، وصلت للحد المسموح من الطلبات. استنى شوية وجرب تاني 🕐\n\n[SERVICE_SUGGESTION] فحص متنقل"
        else:
            return f"❌ عذراً يا {user_name}، حدث خطأ: {error_msg[:100]}\n\n[SERVICE_SUGGESTION] فحص متنقل"

def read_html_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return f"<h1>{filename} غير موجود</h1>"

# ========== صفحات الموقع ==========
@app.get("/")
async def root():
    return RedirectResponse(url="/onboarding.html")

@app.get("/onboarding.html")
async def onboarding():
    return HTMLResponse(content=read_html_file("onboarding.html"))

@app.get("/auth.html")
async def auth():
    return HTMLResponse(content=read_html_file("auth.html"))

@app.get("/dashboard.html")
async def dashboard():
    return HTMLResponse(content=read_html_file("dashboard.html"))

@app.get("/admin.html")
async def admin():
    return HTMLResponse(content=read_html_file("admin.html"))

@app.get("/forget-password.html")
async def forget_password():
    return HTMLResponse(content=read_html_file("forget-password.html"))

@app.get("/verify-code.html")
async def verify_code():
    return HTMLResponse(content=read_html_file("verify-code.html"))

@app.get("/reset-password.html")
async def reset_password():
    return HTMLResponse(content=read_html_file("reset-password.html"))

# ========== API المصادقة ==========
@app.post("/api/signup")
async def api_signup(name: str = Form(...), email: str = Form(...), phone: str = Form(...), password: str = Form(...)):
    result = save_user(name, email, phone, password)
    return result

@app.post("/api/login")
async def api_login(email: str = Form(...), password: str = Form(...)):
    user = get_user(email, password)
    if user:
        return {"success": True, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "phone": user["phone"]}}
    else:
        return {"success": False, "error": "البريد الإلكتروني أو كلمة المرور غير صحيحة"}

# ========== API الحجوزات ==========
@app.post("/api/booking")
async def api_booking(user_id: int = Form(...), service: str = Form(...), name: str = Form(...), phone: str = Form(...), location: str = Form(...), date_time: str = Form(...), car_details: str = Form("")):
    booking_id = save_booking(user_id, service, name, phone, location, date_time, car_details)
    return {"success": True, "booking_id": booking_id}

@app.get("/api/bookings/{user_id}")
async def api_get_bookings(user_id: int):
    bookings = get_user_bookings(user_id)
    return {"success": True, "bookings": bookings}

@app.delete("/api/booking/{booking_id}/{user_id}")
async def api_delete_booking(booking_id: int, user_id: int):
    result = delete_booking(booking_id, user_id)
    return {"success": result}

# ========== API السيارة ==========
@app.post("/api/save-car")
async def api_save_car(user_id: int = Form(...), car_make: str = Form(...), car_model: str = Form(...), car_year: str = Form(...), car_engine: str = Form("")):
    result = save_user_car(user_id, car_make, car_model, car_year, car_engine)
    return {"success": result}

@app.get("/api/get-car/{user_id}")
async def api_get_car(user_id: int):
    car = get_user_car(user_id)
    return {"success": True, "car": car}

# ========== API الشات ==========
@app.post("/api/chat")
async def api_chat(user_id: int = Form(...), message: str = Form(...), image: str = Form(None)):
    print(f"📨 استقبال: user_id={user_id}, message={message[:50] if message else 'None'}, image={'Yes' if image else 'No'}")
    
    # جلب أو إنشاء سجل المحادثة للمستخدم
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # إضافة رسالة المستخدم للسجل
    user_conversations[user_id].append(f"المستخدم: {message}")
    
    # تحديد ما إذا كان السجل طويل جداً (نحتفظ بآخر 15 رسالة بس)
    if len(user_conversations[user_id]) > 15:
        user_conversations[user_id] = user_conversations[user_id][-15:]
    
    try:
        # جلب اسم المستخدم
        user_name = "عميل"
        try:
            user_data = get_user_by_id(user_id)
            if user_data and user_data.get("name"):
                user_name = user_data["name"]
        except:
            pass
        
        # جلب معلومات سيارة المستخدم
        car_info = None
        try:
            car_info = get_user_car(user_id)
        except:
            pass
        
        # إذا كان البوت بيسأل عن نوع العربية والمستخدم جاوب، نحفظ المعلومات
        msg_lower = message.lower()
        car_brands = ["تويوتا", "هيونداي", "مرسيدس", "نيسان", "شيفروليه", "كيا", "bmw", "بي ام دبليو", "فولكس", "مازدا", "هوندا", "ميتسوبيشي", "جيلي", "شيري", "بيجو", "رينو"]
        
        if car_info is None or not car_info.get("car_make"):
            for brand in car_brands:
                if brand in msg_lower:
                    # استخراج نوع العربية من الرسالة
                    car_make = brand
                    car_model = ""
                    words = message.split()
                    for i, word in enumerate(words):
                        if word == brand and i+1 < len(words):
                            car_model = words[i+1]
                            break
                    try:
                        save_user_car(user_id, car_make, car_model, "", "")
                        car_info = {"car_make": car_make, "car_model": car_model, "car_year": "", "car_engine": ""}
                        user_conversations[user_id].append(f"النظام: تم حفظ معلومات السيارة - {car_make} {car_model}")
                    except:
                        pass
                    break
        
        full = diagnose_with_gemini(message, image, user_name, user_id, car_info, user_conversations[user_id])
        
        # إضافة رد البوت للسجل (مختصر عشان ما يطولش)
        diag_clean = re.sub(r'\n?\[SERVICE_SUGGESTION\].*', '', full)
        user_conversations[user_id].append(f"كار إكسبيرت: {diag_clean[:300]}")
        
        # استخراج الخدمة المقترحة
        sug = None
        match = re.search(r'\[SERVICE_SUGGESTION\]\s*(.+)', full)
        if match:
            for key in SERVICES.keys():
                if key in match.group(1) or match.group(1) in key:
                    sug = key
                    break
        
        diag = re.sub(r'\n?\[SERVICE_SUGGESTION\].*', '', full)
        
        # حفظ المحادثة في قاعدة البيانات
        try:
            save_chat_message(user_id, message, diag, image)
        except:
            pass
        
        return {"diagnosis": diag.strip().replace(chr(10), '<br>'), "suggestion": sug}
    except Exception as e:
        print(f"❌ خطأ في api_chat: {e}")
        return {"diagnosis": f"❌ خطأ: {str(e)}", "suggestion": None}

@app.get("/api/chat/history/{user_id}")
async def api_get_chat_history(user_id: int):
    history = get_chat_history(user_id)
    return {"success": True, "history": history}

@app.delete("/api/chat/clear/{user_id}")
async def api_clear_chat_history(user_id: int):
    count = clear_chat_history(user_id)
    if user_id in user_conversations:
        user_conversations[user_id] = []
    return {"success": True, "deleted": count}

# ========== API تحويل الصور ==========
@app.post("/api/change-color")
async def api_change_color(car_image: UploadFile = File(...), color: str = Form(...)):
    try:
        filename = f"temp_car_{random.randint(1000,9999)}.jpg"
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(await car_image.read())
        
        result_path = change_car_color(filepath, color)
        
        if result_path:
            return {"success": True, "result_image": result_path, "message": f"✅ تم تغيير اللون إلى {color}"}
        else:
            return {"success": False, "error": "فشل في تغيير اللون"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/add-accessory")
async def api_add_accessory(car_image: UploadFile = File(...), accessory_type: str = Form(...), position: str = Form("front")):
    try:
        filename = f"temp_car_{random.randint(1000,9999)}.jpg"
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(await car_image.read())
        
        result_path = add_accessory_to_car(filepath, accessory_type, position)
        
        if result_path:
            return {"success": True, "result_image": result_path, "message": f"✅ تم إضافة {accessory_type} بنجاح"}
        else:
            return {"success": False, "error": "فشل في إضافة الأكسسوار"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== API المدير (Admin) ==========
@app.get("/api/admin/stats")
async def admin_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cursor.fetchone()[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE date(date_time) = ?", (today,))
    today_bookings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM chat_history")
    total_chats = cursor.fetchone()[0]
    
    conn.close()
    
    return {"success": True, "stats": {
        "totalUsers": total_users,
        "totalBookings": total_bookings,
        "todayBookings": today_bookings,
        "totalChats": total_chats
    }}

@app.get("/api/admin/users")
async def admin_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    return {"success": True, "users": [dict(u) for u in users]}

@app.get("/api/admin/bookings")
async def admin_bookings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, u.name as user_name 
        FROM bookings b 
        LEFT JOIN users u ON b.user_id = u.id 
        ORDER BY b.created_at DESC
    """)
    bookings = cursor.fetchall()
    conn.close()
    return {"success": True, "bookings": [dict(b) for b in bookings]}

@app.get("/api/admin/chats")
async def admin_chats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, u.name as user_name 
        FROM chat_history c 
        LEFT JOIN users u ON c.user_id = u.id 
        ORDER BY c.created_at DESC LIMIT 100
    """)
    chats = cursor.fetchall()
    conn.close()
    return {"success": True, "chats": [dict(c) for c in chats]}

@app.put("/api/admin/booking/{booking_id}/status")
async def admin_update_booking_status(booking_id: int, request: Request):
    data = await request.json()
    status = data.get("status")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/admin/user/{user_id}")
async def admin_delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/admin/booking/{booking_id}")
async def admin_delete_booking(booking_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)