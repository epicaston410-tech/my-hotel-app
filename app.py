import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import date, datetime
import io
import os
import base64

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอ", layout="wide")

# เชื่อมต่อ Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- ฟังก์ชันรูปภาพ (คงเดิม) ---
def get_image_base64(image_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "static", image_name)
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_image_base64("dopa.png")
img_src = f"data:image/png;base64,{img_base64}" if img_base64 else "https://raw.githubusercontent.com/streamlit/proactive-connectors/main/branding/logo.png"

# หัวข้อระบบ (คงเดิม)
st.html(f"""
    <div style='display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 10px;'>
        <img src='{img_src}' style='width: 100px; height: auto;' onerror="this.src='https://img.icons8.com/color/96/000000/goverment.png';">
        <div style='text-align: left;'>
            <h1 style='font-size: 38px; font-weight: bold; margin: 0 0 5px 0; color: #FFFFFF;'>🏨 &nbsp;ระบบงานทะเบียนโรงแรม</h1>
            <h2 style='font-size: 24px; font-weight: normal; color: #CCCCCC; margin: 0;'>กรมการปกครอง ที่ว่าการอำเภอเมืองประจวบคีรีขันธ์</h2>
        </div>
    </div>
""")
st.markdown("---")

# รายการตัวเลือก (คงเดิม)
SUBDISTRICTS = ["ตำบลเกาะหลัก", "ตำบลอ่าวน้อย", "ตำบลคลองวาฬ", "ตำบลห้วยทราย", "ตำบลบ่อนอก", "เขตเทศบาลเมืองประจวบคีรีขันธ์"]
HOTEL_TYPES = ["ประเภท 1 (เฉพาะห้องพัก)", "ประเภท 2 (ห้องพัก + ห้องอาหาร)", "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", "ประเภท 4", "ประเภท 5 ไม่เป็นโรงแรม"]
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

# --- ฟังก์ชัน Supabase ---
def load_data():
    # ดึงข้อมูลแบบ Join ตาราง
    res = supabase.table("hotels").select("*, licenses(*)").execute()
    data = []
    for h in res.data:
        row = {
            'รหัสระบบ': h['id'],
            'เลขที่ใบอนุญาต (ร.บ.2)': h['licenses'][0]['license_no'] if h['licenses'] else "",
            'ชื่อโรงแรม': h['hotel_name'],
            'ประเภทโรงแรม': h['hotel_type'],
            'ชื่อผู้ประกอบการ': h['owner_name'],
            'ชื่อผู้จัดการโรงแรม (หน้างาน)': h['manager_name'],
            'จำนวนห้องพัก': h['total_rooms'],
            'วันออกใบอนุญาต': h['licenses'][0]['issue_date'] if h['licenses'] else "",
            'วันหมดอายุ': h['licenses'][0]['expiry_date'] if h['licenses'] else "",
            'สถานะค่าธรรมเนียมรายปี': h['licenses'][0]['fee_status'] if h['licenses'] else "",
            'ที่อยู่': h['address'],
            'เบอร์โทรศัพท์เจ้าของ': h['tel'],
            'เบอร์โทรศัพท์ผู้จัดการ': h['manager_tel']
        }
        data.append(row)
    return pd.DataFrame(data)

# --- ส่วนหน้าจอหลัก (คงโครงสร้างเดิม) ---
tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงาน", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

with tab1:
    df_source = load_data()
    if not df_source.empty:
        # คำนวณวันหมดอายุเหมือนเดิม
        today = date.today()
        # ... (ส่วนคำนวณวันคงเหลือคงเดิม) ...
        # [พี่สามารถนำ Logic คำนวณวันคงเหลือจากโค้ดเดิมมาใส่ตรงนี้ได้เลยครับ]
        
        # ค้นหา / ตาราง / แก้ไข / ลบ (ให้เปลี่ยนจากการใช้ conn.execute() มาเป็น supabase.table(...).update()... )
        # ตัวอย่างการลบ:
        # supabase.table("hotels").delete().eq("id", selected_id).execute()
        
        st.dataframe(df_source, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ")

with tab2:
    with st.form("hotel_add_form", clear_on_submit=True):
        # ฟอร์มเพิ่มข้อมูล...
        submit_btn = st.form_submit_button("💾 บันทึกข้อมูล")
        if submit_btn:
            # เพิ่มโรงแรม
            new_h = supabase.table("hotels").insert({"hotel_name": h_name, ...}).execute()
            # เพิ่มใบอนุญาต
            supabase.table("licenses").insert({"hotel_id": new_h.data[0]['id'], ...}).execute()
            st.success("บันทึกสำเร็จ")
