import streamlit as st
import pandas as pd
import sqlite3
import os

# ตั้งค่าหน้าจอให้เป็นแนวกว้าง และเปลี่ยนโทนเป็น Dark Mode อัตโนมัติ
st.set_page_config(page_title="ระบบฐานข้อมูลโรงแรม", layout="wide")

# ฟังก์ชันเชื่อมต่อฐานข้อมูล SQLite
def get_db_connection():
    # ระบบจะสร้างไฟล์ database.db ขึ้นมาโดยอัตโนมัติถ้าไม่มีไฟล์อยู่
    conn = sqlite3.connect('database.db')
    return conn

# ฟังก์ชันเริ่มต้นระบบ: สร้างตารางและอัปเดตโครงสร้างตาราง
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. สร้างตารางพื้นฐานในกรณีที่เป็นการเปิดใช้งานครั้งแรก
    c.execute('''
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT NOT NULL,
            owner_name TEXT,
            owner_phone TEXT,
            manager_name TEXT,
            manager_phone TEXT,
            province TEXT,
            amphoe TEXT,
            tambon TEXT,
            address_detail TEXT
        )
    ''')
    
    # 2. สูตรลับป้องกันระบบพัง: ตรวจสอบและเพิ่มคอลัมน์ผู้จัดการอัตโนมัติ (กรณีพี่ใช้ฐานข้อมูลเดิมบนคลาวด์)
    c.execute("PRAGMA table_info(hotels)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'manager_name' not in columns:
        c.execute("ALTER TABLE hotels ADD COLUMN manager_name TEXT")
    if 'manager_phone' not in columns:
        c.execute("ALTER TABLE hotels ADD COLUMN manager_phone TEXT")
        
    conn.commit()
    conn.close()

# รันระบบฐานข้อมูลตอนเปิดแอป
init_db()

# --- ส่วนของหน้าตาโปรแกรม (UI) ---
st.title("🏨 ระบบจัดการและบันทึกข้อมูลข้อมูลโรงแรม")
st.markdown("---")

# แบ่งหน้าจอทำงานออกเป็น 2 แท็บ: แท็บกรอกข้อมูล และ แท็บแสดงผล/ค้นหา
tab1, tab2 = st.tabs(["📝 บันทึกข้อมูลโรงแรมใหม่", "🔍 ค้นหาและดูข้อมูลทั้งหมด"])

# ================= แท็บที่ 1: หน้ากรอกข้อมูล =================
with tab1:
    st.subheader("กรอกรายละเอียดโรงแรม")
    
    # ใช้ระบบคอลัมน์เพื่อจัดกลุ่มกล่องข้อความให้ดูสวยงามไม่รกตา
    col1, col2 = st.columns(2)
    
    with col1:
        hotel_name = st.text_input("🏢 ชื่อสถานประกอบการ / ชื่อโรงแรม", placeholder="กรอกชื่อโรงแรม...")
        owner_name = st.text_input("👤 ชื่อเจ้าของโรงแรม (ผู้รับใบอนุญาต)", placeholder="ชื่อ-นามสกุล เจ้าของ...")
        owner_phone = st.text_input("📞 เบอร์โทรศัพท์เจ้าของโรงแรม", placeholder="08x-xxxxxxx")
        
    with col2:
        # --- จุดที่เพิ่มใหม่ตามโจทย์ของพี่ ---
        manager_name = st.text_input("👔 ชื่อผู้จัดการโรงแรม (หน้างาน)", placeholder="ชื่อ-นามสกุล ผู้จัดการ...")
        manager_phone = st.text_input("📱 เบอร์โทรศัพท์ผู้จัดการ (ติดต่อด่วน)", placeholder="08x-xxxxxxx")
        # ----------------------------------
        address_detail = st.text_area("📍 ที่อยู่รายละเอียดเพิ่มเติม (เลขที่, ถนน, ซอย)", placeholder="เช่น 123/4 ม.5 ต.โคกขาม...")

    st.markdown("##### 🌐 พื้นที่ที่ตั้ง")
    col3, col4, col5 = st.columns(3)
    with col3:
        province = st.text_input("จังหวัด", value="ประจวบคีรีขันธ์")
    with col4:
        amphoe = st.text_input("อำเภอ / เขต")
    with col5:
        tambon = st.text_input("ตำบล / แขวง")

    # ปุ่มกดบันทึกข้อมูล
    if st.button("💾 บันทึกข้อมูลเข้าสู่ระบบ", type="primary"):
        if hotel_name:  # ป้องกันการกดบันทึกโดยไม่มีชื่อโรงแรม
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO hotels (
                    hotel_name, owner_name, owner_phone, manager_name, manager_phone, 
                    province, amphoe, tambon, address_detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (hotel_name, owner_name, owner_phone, manager_name, manager_phone, 
                  province, amphoe, tambon, address_detail))
            conn.commit()
            conn.close()
            st.success(f"🎉 บันทึกข้อมูลโรงแรม '{hotel_name}' เรียบร้อยแล้ว!")
        else:
            st.error("⚠️ กรุณากรอกชื่อโรงแรมก่อนกดบันทึกครับ")

# ================= แท็บที่ 2: หน้าโชว์ผลลัพธ์และค้นหา =================
with tab2:
    st.subheader("🔎 ค้นหาและตรวจสอบข้อมูลโรงงาน/โรงแรม")
    
    # ช่องค้นหาอัจฉริยะ (ค้นหาได้จากชื่อโรงแรม, อำเภอ หรือตำบล)
    search_query = st.text_input("พิมพ์ชื่อโรงแรม, อำเภอ หรือ ตำบล เพื่อค้นหาด่วน...", placeholder="เช่น หัวหิน, กุยบุรี...")
    
    conn = get_db_connection()
    # ดึงข้อมูลทั้งหมดออกมาก่อน
    df = pd.read_sql_query("SELECT * FROM hotels", conn)
    conn.close()
    
    if not df.empty:
        # ระบบคัดกรองข้อมูลตามคำค้นหา
        if search_query:
            df = df[
                df['hotel_name'].str.contains(search_query, case=False, na=False) |
                df['amphoe'].str.contains(search_query, case=False, na=False) |
                df['tambon'].str.contains(search_query, case=False, na=False)
            ]
        
        # --- ล็อกเป้าหน้าโชว์: แสดงเฉพาะ ชื่อโรงแรม, ผู้จัดการ, เบอร์ผู้จัดการ และที่อยู่ตามโจทย์พี่ ---
        # รวมที่อยู่เป็นข้อความยาวเส้นเดียวให้อ่านง่าย
        df['ที่อยู่ตั้ง'] = df['address_detail'] + " ต." + df['tambon'] + " อ." + df['amphoe'] + " จ." + df['province']
        
        # คัดเอาคอลัมน์ที่จะไปแสดงผลหน้าบ้าน (ซ่อนชื่อเจ้าของและเบอร์เจ้าของไว้เบื้องหลัง)
        df_display = df[['hotel_name', 'manager_name', 'manager_phone', 'ที่อยู่ตั้ง']].copy()
        
        # เปลี่ยนชื่อหัวตารางให้เป็นภาษาไทยหรูหราอ่านง่าย
        df_display.columns = ['🏢 ชื่อโรงแรม', '👔 ผู้จัดการโรงแรม', '📱 เบอร์โทรศัพท์ผู้จัดการ', '📍 ที่อยู่และพิกัดที่ตั้ง']
        
        # แสดงตารางข้อมูลบนหน้าเว็บ
        st.dataframe(df_display, use_container_width=True)
        
        # ฟีเจอร์ดาวน์โหลดไฟล์ Excel (สืบทอดความต้องการเดิม)
        st.markdown("---")
        st.subheader("📥 ส่งออกข้อมูล")
        
        # ทำปุ่มโหลดไฟล์ Excel
        @st.cache_data
        def convert_df_to_excel(excel_df):
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                excel_df.to_excel(writer, index=False, sheet_name='รายชื่อโรงแรม')
            return output.getvalue()
            
        excel_data = convert_df_to_excel(df_display)
        
        st.download_button(
            label="📥 ดาวน์โหลดข้อมูลทั้งหมดเป็นไฟล์ Excel (.xlsx)",
            data=excel_data,
            file_name="รายชื่อโรงแรมและผู้จัดการล่าสุด.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("ℹ️ ยังไม่มีข้อมูลบันทึกในระบบในขณะนี้")
