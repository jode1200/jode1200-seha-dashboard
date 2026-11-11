import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import pytesseract
from PIL import Image
import re
import time

# إعدادات الصفحة
st.set_page_config(page_title="النظام المتكامل للتحقق من الإجازات", layout="wide")
st.title("🏥 النظام المتكامل: OCR + الاستعلام الآلي من صحتي")

# دالة الاستعلام الآلي
def check_seha_automated(leave_id, national_id):
    result = {"status": "error", "message": ""}
    
    with sync_playwright() as p:
        # headless=True ليعمل في الخلفية (مطلوب للاستضافة السحابية)
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        try:
            page.goto("https://slenquiry.seha.sa/Home/SickLeave", timeout=20000)
            page.fill('input[name="ServiceCode"]', leave_id)
            page.fill('input[name="IdNumber"]', national_id)
            page.click('button[type="submit"]')
            
            # انتظار النتيجة
            page.wait_for_selector('table, .alert-danger', timeout=15000)
            
            if page.is_visible('table'):
                result["status"] = "valid"
                result["message"] = "✅ الإجازة سليمة ومسجلة في منصة صحتي الرسمية."
            else:
                result["status"] = "invalid"
                result["message"] = "❌ الإجازة غير موجودة أو البيانات غير صحيحة (مزورة)."
        except Exception as e:
            result["status"] = "invalid"
            result["message"] = "❌ فشل الاستعلام: الرقم غير موجود أو حدث خطأ في الاتصال."
        finally:
            browser.close()
    return result

# واجهة المستخدم
uploaded_file = st.file_uploader("قم برفع صورة الإجازة المرضية (JPG, PNG)", type=["jpg", "png"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 المستند المرفوع")
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)
        
        st.info("⏳ جاري استخراج النص (OCR)...")
        # استخراج النص (يتطلب تثبيت Tesseract في السيرفر)
        text = pytesseract.image_to_string(image, lang='eng+ara')
        
        # البحث عن رمز الإجازة (PSL أو GSL) ورقم الهوية باستخدام Regex
        leave_id_match = re.search(r'(PSL|GSL)\d{11,14}', text)
        id_match = re.search(r'\b\d{10}\b', text) # رقم هوية من 10 أرقام
        
        leave_id = leave_id_match.group(0) if leave_id_match else ""
        national_id = id_match.group(0) if id_match else ""
        
        st.write(f"**رمز الإجازة المستخرج:** `{leave_id}`")
        st.write(f"**رقم الهوية المستخرج:** `{national_id}`")

    with col2:
        st.subheader("⚙️ نتيجة التحقق الآلي")
        if st.button("🚀 بدء الاستعلام من صحتي", type="primary", use_container_width=True):
            if not leave_id or not national_id:
                st.error("⚠️ لم يتمكن النظام من استخراج الرمز أو الهوية من الصورة. يرجى إدخالها يدوياً بالأسفل.")
                leave_id = st.text_input("رمز الإجازة يدوياً:")
                national_id = st.text_input("رقم الهوية يدوياً:")
                if st.button("تأكيد وإرسال"):
                     pass # يمكن إضافة منطق الإرسال هنا
            else:
                with st.spinner("جاري الاتصال بموقع صحتي الرسمي..."):
                    res = check_seha_automated(leave_id, national_id)
                    if res["status"] == "valid":
                        st.success(res["message"])
                        st.balloons()
                    else:
                        st.error(res["message"])
                        st.warning("🚨 تم رفض الإجازة وتحويلها للمراجعة.")