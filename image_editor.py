import cv2
import numpy as np
import os
import random

def change_car_color(image_path, target_color):
    """
    تغيير لون السيارة في الصورة فعلياً
    """
    try:
        # فتح الصورة
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # ألوان RGB للهدف
        color_map = {
            "أحمر": (255, 50, 50),
            "أزرق": (50, 50, 255),
            "أسود": (30, 30, 30),
            "أبيض": (245, 245, 245),
            "أصفر": (255, 255, 50),
            "أخضر": (50, 255, 50),
            "فضي": (192, 192, 192),
            "ذهبي": (255, 215, 0),
            "برتقالي": (255, 165, 0),
            "بنفسجي": (128, 0, 128)
        }
        
        target_rgb = color_map.get(target_color, (255, 50, 50))
        
        # تحويل الصورة إلى HSV
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # إنشاء ماسك للسيارة (تحديد المناطق ذات اللون السائد)
        lower = np.array([0, 0, 0])
        upper = np.array([180, 255, 100])
        mask = cv2.inRange(hsv, lower, upper)
        
        # تحسين الماسك
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.erode(mask, kernel, iterations=1)
        
        # إنشاء صورة باللون الجديد
        color_layer = np.zeros_like(img_rgb)
        color_layer[:] = target_rgb
        
        # تطبيق اللون الجديد
        mask_3channel = cv2.merge([mask, mask, mask])
        result = np.where(mask_3channel == 255, color_layer, img_rgb)
        
        # حفظ الصورة
        output_filename = f"colored_car_{random.randint(1000,9999)}.png"
        output_path = os.path.join("uploads", output_filename)
        
        result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, result_bgr)
        
        return f"/uploads/{output_filename}"
        
    except Exception as e:
        print(f"❌ خطأ في تغيير اللون: {e}")
        return None

def add_accessory_to_car(image_path, accessory_type, position):
    """
    إضافة أكسسوار على السيارة
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        height, width = img.shape[:2]
        
        # تحديد موقع الأكسسوار
        pos_map = {
            "front": (int(width * 0.65), int(height * 0.1)),
            "back": (int(width * 0.25), int(height * 0.1)),
            "roof": (int(width * 0.4), int(height * 0.05)),
            "wheels": (int(width * 0.15), int(height * 0.7))
        }
        
        x, y = pos_map.get(position, (int(width * 0.4), int(height * 0.3)))
        
        # حجم الأكسسوار
        size = int(min(width, height) * 0.15)
        
        # ألوان الأكسسوارات
        accessory_colors = {
            "جنوط رياضية": (200, 200, 200),
            "جناح خلفي": (255, 100, 100),
            "إضاءة LED": (255, 255, 100),
            "مصد أمامي": (100, 100, 200),
            "شبك أمامي": (150, 150, 150)
        }
        
        color = accessory_colors.get(accessory_type, (0, 255, 0))
        
        # رسم الأكسسوار
        cv2.rectangle(img, (x, y), (x + size, y + size), color, -1)
        cv2.rectangle(img, (x, y), (x + size, y + size), (255, 255, 255), 2)
        
        # حفظ الصورة
        output_filename = f"accessory_car_{random.randint(1000,9999)}.png"
        output_path = os.path.join("uploads", output_filename)
        cv2.imwrite(output_path, img)
        
        return f"/uploads/{output_filename}"
        
    except Exception as e:
        print(f"❌ خطأ في إضافة الأكسسوار: {e}")
        return None