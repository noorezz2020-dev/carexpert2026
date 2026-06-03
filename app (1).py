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
    save_user, get_user, get_user_by_id, update_user_profile,
    save_booking, get_user_bookings, delete_booking,
    save_chat_message, get_chat_history, clear_chat_history,
    get_db_connection, save_user_car, get_user_car,
    get_system_stats, update_system_stats
)

app = FastAPI()

# إنشاء المجلدات
for folder in ["static", "uploads", "profiles"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/profiles", StaticFiles(directory="profiles"), name="profiles")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "AIzaSyBnV8Ql2IVmoL1jaxfza1ElkDxZs-wFUS0"

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

# تخزين مؤقت للمحادثات
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

def get_service_from_problem(problem):
    """تحديد الخدمة المناسبة بناءً على المشكلة"""
    problem_lower = problem.lower()
    service_map = {
        "زيت": "صيانة دورية",
        "فرامل": "فحص متنقل",
        "بطارية": "خدمات متنقلة",
        "كاوتش": "خدمات متنقلة",
        "إطار": "خدمات متنقلة",
        "غسيل": "غسيل احترافي",
        "لون": "غسيل احترافي",
        "اكسسوار": "إكسسوارات",
        "جنوط": "إكسسوارات",
        "تأجير": "تأجير",
        "صوت": "فحص متنقل",
        "محرك": "فحص متنقل",
        "لمبة": "فحص متنقل",
        "دوران": "خدمات متنقلة"
    }
    for key, service in service_map.items():
        if key in problem_lower:
            return service
    return "فحص متنقل"

def diagnose_with_gemini(problem, image_base64=None, user_name="عميل", user_id=None, car_info=None, conversation_history=None):
    """تحليل المشكلة باستخدام Gemini - ردود مفصلة 100%"""
    
    problem_lower = problem.lower()
    suggested_service = get_service_from_problem(problem)
    service_desc = SERVICES.get(suggested_service, "فحص متنقل")
    
    if not GEMINI_AVAILABLE:
        return f"⚠️ عذراً يا {user_name}، خدمة الذكاء الاصطناعي غير متاحة حالياً.\n\n💡 **الخدمة المناسبة:** {service_desc}\n\n[SERVICE_SUGGESTION] {suggested_service}"
    
    # بناء سياق المحادثة
    context = ""
    if conversation_history:
        recent = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        context = "\n".join(recent)
        context = f"\n\nسجل المحادثة السابقة:\n{context}\n"
    
    # معلومات السيارة
    car_context = ""
    if car_info and car_info.get("car_make"):
        car_context = f"""\nمعلومات سيارة {user_name}:
- الماركة: {car_info.get('car_make', 'غير معروف')}
- الموديل: {car_info.get('car_model', 'غير معروف')}
- السنة: {car_info.get('car_year', 'غير معروف')}
"""
    
    services_list = """
خدماتنا المتاحة في Car Expert:
1. 🔍 فحص السيارة في موقع العميل
2. 📋 فحص شامل للسيارات المستعملة
3. 🧼 غسيل السيارات بأحدث التقنيات
4. 🎨 تركيب إكسسوارات - فريق متنقل
5. 🚙 تأجير سيارات للشركات
6. 🛠️ حجز موعد صيانة
7. ⏰ مواعيد صيانة دورية (زيت - إطارات)
8. ⚡ فريق طوارئ - بطاريات وإطارات 24/7
"""
    
    try:
        contents = []
        
        # تعليمات واضحة لـ Gemini
        system_prompt = f"""أنت خبير سيارات محترف وودود اسمك "كار إكسبيرت". اتكلم مع {user_name} بالعامية المصرية.

مهمتك:
1. حلل مشكلة العميل بالتفصيل
2. اذكر الأسباب المحتملة (3-5 أسباب)
3. حدد درجة الخطورة (بسيطة/متوسطة/عالية/خطيرة)
4. اقترح حلول عملية خطوة بخطوة
5. في النهاية، اذكر الخدمة المناسبة من القائمة

{car_context}

الخدمات المتاحة:
{services_list}

{context}

العميل قال: {problem}

رد عليه برد طويل ومفيد (على الأقل 150 كلمة) يتضمن تحليل دقيق ونصائح قيمة:"""
        contents.append(system_prompt)
        
        # إضافة الصورة لو موجودة
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
        
        # إضافة الخدمة المقترحة في النهاية
        full_response = response.text
        if "[SERVICE_SUGGESTION]" not in full_response:
            full_response += f"\n\n💡 **الخدمة المناسبة:** {service_desc}\n\n[SERVICE_SUGGESTION] {suggested_service}"
        
        return full_response
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ خطأ في Gemini: {error_msg}")
        
        # لو فيه خطأ، استخدم رد مبرمج
        return f"📝 {user_name}، شكراً لتواصلك.\n\nمشكلتك: {problem}\n\n🔧 فريق Car Expert سيتواصل معك قريباً.\n\n💡 **الخدمة المناسبة:** {service_desc}\n\n[SERVICE_SUGGESTION] {suggested_service}"

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

@app.get("/contact.html")
async def contact():
    return HTMLResponse(content=read_html_file("contact.html"))

@app.get("/about.html")
async def about():
    return HTMLResponse(content=read_html_file("about.html"))

@app.get("/faq.html")
async def faq():
    return HTMLResponse(content=read_html_file("faq.html"))

@app.get("/privacy.html")
async def privacy():
    return HTMLResponse(content=read_html_file("privacy.html"))

@app.get("/terms.html")
async def terms():
    return HTMLResponse(content=read_html_file("terms.html"))

@app.get("/404.html")
async def not_found():
    return HTMLResponse(content=read_html_file("404.html"))

# ========== API المصادقة ==========
@app.post("/api/signup")
async def api_signup(name: str = Form(...), email: str = Form(...), phone: str = Form(...), password: str = Form(...)):
    result = save_user(name, email, phone, password)
    return result

@app.post("/api/login")
async def api_login(email: str = Form(...), password: str = Form(...)):
    user = get_user(email, password)
    if user:
        return {"success": True, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "phone": user["phone"], "is_admin": user.get("is_admin", 0), "profile_image": user.get("profile_image")}}
    else:
        return {"success": False, "error": "البريد الإلكتروني أو كلمة المرور غير صحيحة"}

@app.get("/api/user/{user_id}")
async def api_get_user(user_id: int):
    user = get_user_by_id(user_id)
    if user:
        return {"success": True, "user": user}
    return {"success": False, "error": "المستخدم غير موجود"}

@app.post("/api/user/update")
async def api_update_user(user_id: int = Form(...), name: str = Form(...), email: str = Form(...), phone: str = Form(...)):
    result = update_user_profile(user_id, name, email, phone)
    return {"success": result}

@app.post("/api/user/upload-photo")
async def api_upload_photo(user_id: int = Form(...), photo: UploadFile = File(...)):
    try:
        ext = photo.filename.split('.')[-1]
        filename = f"user_{user_id}_{random.randint(1000,9999)}.{ext}"
        filepath = os.path.join("profiles", filename)
        with open(filepath, "wb") as f:
            f.write(await photo.read())
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_image = ? WHERE id = ?", (f"/profiles/{filename}", user_id))
        conn.commit()
        conn.close()
        return {"success": True, "image_url": f"/profiles/{filename}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

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

# ========== API إحصائيات النظام ==========
@app.get("/api/stats")
async def api_get_stats():
    stats = get_system_stats()
    return {"success": True, "stats": stats}

# ========== API الشات (المعدل) ==========
@app.post("/api/chat")
async def api_chat(user_id: int = Form(...), message: str = Form(...), image: str = Form(None)):
    print(f"📨 استقبال: user_id={user_id}, message={message[:50] if message else 'None'}, image={'Yes' if image else 'No'}")
    
    # جلب أو إنشاء سجل المحادثة للمستخدم
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # إضافة رسالة المستخدم للسجل
    user_conversations[user_id].append(f"المستخدم: {message}")
    if len(user_conversations[user_id]) > 15:
        user_conversations[user_id] = user_conversations[user_id][-15:]
    
    # جلب اسم المستخدم
    user_name = "عميل"
    try:
        user_data = get_user_by_id(user_id)
        if user_data and user_data.get("name"):
            user_name = user_data["name"]
    except:
        pass
    
    # جلب معلومات السيارة
    car_info = None
    try:
        car_info = get_user_car(user_id)
    except:
        pass
    
    # معالجة الطلب
    full = diagnose_with_gemini(message, image, user_name, user_id, car_info, user_conversations[user_id])
    
    # استخراج الخدمة المقترحة
    sug = get_service_from_problem(message)
    
    # إضافة رد البوت للسجل
    user_conversations[user_id].append(f"كار إكسبيرت: {full[:300]}")
    
    # حفظ المحادثة في قاعدة البيانات
    try:
        save_chat_message(user_id, message, full, image)
    except:
        pass
    
    return {"diagnosis": full.strip().replace(chr(10), '<br>'), "suggestion": sug}

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
        filename = f"temp_{random.randint(1000,9999)}.jpg"
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(await car_image.read())
        result_path = change_car_color(filepath, color)
        if result_path:
            return {"success": True, "result_image": result_path}
        return {"success": False, "error": "فشل في تغيير اللون"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/add-accessory")
async def api_add_accessory(car_image: UploadFile = File(...), accessory_type: str = Form(...), position: str = Form("front")):
    try:
        filename = f"temp_{random.randint(1000,9999)}.jpg"
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(await car_image.read())
        result_path = add_accessory_to_car(filepath, accessory_type, position)
        if result_path:
            return {"success": True, "result_image": result_path}
        return {"success": False, "error": "فشل في إضافة الأكسسوار"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== API المدير (Admin Only) ==========
def is_admin_user(user_id):
    user = get_user_by_id(user_id)
    return user and user.get("is_admin") == 1

@app.post("/api/admin/update-stats")
async def admin_update_stats(admin_id: int = Form(...), total_services: int = Form(...), active_teams: int = Form(...), avg_response_time: int = Form(...)):
    if not is_admin_user(admin_id):
        return {"success": False, "error": "غير مصرح به - مدير فقط"}
    result = update_system_stats(total_services, active_teams, avg_response_time)
    return {"success": result}

@app.get("/api/admin/all-users")
async def admin_all_users(admin_id: int):
    if not is_admin_user(admin_id):
        return {"success": False, "error": "غير مصرح به - مدير فقط"}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone, is_admin, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    return {"success": True, "users": [dict(u) for u in users]}

@app.get("/api/admin/all-bookings")
async def admin_all_bookings(admin_id: int):
    if not is_admin_user(admin_id):
        return {"success": False, "error": "غير مصرح به - مدير فقط"}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT b.*, u.name as user_name FROM bookings b LEFT JOIN users u ON b.user_id = u.id ORDER BY b.created_at DESC")
    bookings = cursor.fetchall()
    conn.close()
    return {"success": True, "bookings": [dict(b) for b in bookings]}

@app.get("/api/admin/all-chats")
async def admin_all_chats(admin_id: int):
    if not is_admin_user(admin_id):
        return {"success": False, "error": "غير مصرح به - مدير فقط"}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT c.*, u.name as user_name FROM chat_history c LEFT JOIN users u ON c.user_id = u.id ORDER BY c.created_at DESC LIMIT 100")
    chats = cursor.fetchall()
    conn.close()
    return {"success": True, "chats": [dict(c) for c in chats]}

@app.delete("/api/admin/delete-user")
async def admin_delete_user(user_id: int, admin_id: int):
    if not is_admin_user(admin_id):
        return {"success": False, "error": "غير مصرح به - مدير فقط"}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_cars WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/admin/delete-booking")
async def admin_delete_booking(booking_id: int, admin_id: int):
    if not is_admin_user(admin_id):
        return {"success": False, "error": "غير مصرح به - مدير فقط"}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)