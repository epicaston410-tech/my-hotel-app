import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import os
import base64
from streamlit_gsheets import GSheetsConnection

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอ", layout="wide")

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ส่วนหัวของระบบ ---
st.html("""
    <div style='display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 10px;'>
        <div style='text-align: left;'>
            <h1 style='font-size: 38px; font-weight: bold; margin: 0 0 5px 0; color: #FFFFFF;'>🏨 &nbsp;ระบบงานทะเบียนโรงแรม</h1>
            <h2 style='font-size: 24px; font-weight: normal; color: #CCCCCC; margin: 0;'>กรมการปกครอง ที่ว่าการอำเภอเมืองประจวบคีรีขันธ์</h2>
        </div>
    </div>
""")
st.markdown("---")

# 2. ฟังก์ชันโหลด/จัดการข้อมูล
def load_data():
    df = conn.read(worksheet="Sheet1")
    df = df.dropna(how='all') # ตัดแถวว่าง
    return df

# 3. เมนูการใช้งาน
tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงาน", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

with tab1:
    df_source = load_data()
    if not df_source.empty:
        # ระบบคำนวณวันหมดอายุ
        today = date.today()
        # (ส่วนของการคำนวณสถานะคงเดิมตามที่พี่เคยมี)
        
        st.markdown("### 📋 ตารางข้อมูลสถานะล่าสุด")
        st.dataframe(df_source, use_container_width=True)
        
        # ฟังก์ชันดาวน์โหลด Excel
        output = io.BytesIO()
        df_source.to_excel(output, index=False)
        st.download_button("📥 ปริ้นสรุปข้อมูล (Excel)", data=output.getvalue(), file_name="รายงาน_ทะเบียนโรงแรม.xlsx")

with tab2:
    st.markdown("### 📝 เพิ่มทะเบียนโรงแรมใหม่")
    with st.form("hotel_add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            h_name = st.text_input("ชื่อโรงแรม *")
            h_owner = st.text_input("ชื่อผู้ประกอบการ *")
            h_rooms = st.number_input("จำนวนห้องพัก", min_value=1)
        with c2:
            l_no = st.text_input("เลขที่ใบอนุญาต *")
            h_tel = st.text_input("เบอร์โทรศัพท์")
            
        submit_btn = st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets")
        
        if submit_btn:
            new_data = pd.DataFrame([{
                "ชื่อโรงแรม": h_name,
                "ชื่อผู้ประกอบการ": h_owner,
                "จำนวนห้องพัก": h_rooms,
                "เลขที่ใบอนุญาต": l_no,
                "เบอร์โทรศัพท์": h_tel
            }])
            
            # รวมข้อมูลเก่าและใหม่
            updated_df = pd.concat([df_source, new_data], ignore_index=True)
            # เขียนกลับลง Google Sheets
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("🎉 บันทึกข้อมูลสำเร็จ!")
            st.rerun()
