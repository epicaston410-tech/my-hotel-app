import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import io

# 1. ตั้งค่าหน้าเว็บให้กว้างและสะอาด สไตล์งานราชการ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอ", layout="wide")

# --- แก้ไขจุดพังสำหรับ Python 3.14: ใช้ตารางมาตรฐานจัดตำแหน่งแทนการแบ่งคอลัมน์ซ้อน ---
# ปรับมาใช้ st.html() แทน st.markdown(unsafe_html=True) เพื่อป้องกัน TypeError หน้าจอแดง
st.html("""
    <div style='display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 10px;'>
        <img src='https://stat.bora.dopa.go.th/stat/images/dopa.png' style='width: 100px; height: auto;'>
        <div style='text-align: left;'>
            <h1 style='font-size: 38px; font-weight: bold; margin: 0 0 5px 0; color: #FFFFFF;'>
                🏨 &nbsp;ระบบงานทะเบียนโรงแรม
            </h1>
            <h2 style='font-size: 24px; font-weight: normal; color: #CCCCCC; margin: 0;'>
                กรมการปกครอง ที่ว่าการอำเภอเมืองประจวบคีรีขันธ์
            </h2>
        </div>
    </div>
""")

st.markdown("---")

# 2. ฟังก์ชันเชื่อมต่อฐานข้อมูล SQLite
DB_FILE = "database.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

# ฟังก์ชันสร้างตารางเริ่มต้น
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hotels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_name TEXT NOT NULL,
            hotel_type TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            manager_name TEXT,
            manager_tel TEXT,
            total_rooms INTEGER NOT NULL,
            tel TEXT,
            address TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hotel_id INTEGER,
            license_no TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            fee_status TEXT DEFAULT 'จ่ายแล้ว',
            FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
        )
    """)
    
    # อัปเดตโครงสร้างฐานข้อมูลเดิมป้องกันระบบพัง
    try:
        cursor.execute("ALTER TABLE hotels ADD COLUMN manager_name TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE hotels ADD COLUMN manager_tel TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

# รายการตัวเลือกตำบลในอำเภอเมืองประจวบคีรีขันธ์
SUBDISTRICTS = [
    "ตำบลเกาะหลัก",
    "ตำบลอ่าวน้อย",
    "ตำบลคลองวาฬ",
    "ตำบลห้วยทราย",
    "ตำบลบ่อนอก",
    "เขตเทศบาลเมืองประจวบคีรีขันธ์"
]

# ตัวเลือกประเภทโรงแรม
HOTEL_TYPES = [
    "ประเภท 1 (เฉพาะห้องพัก)", 
    "ประเภท 2 (ห้องพัก + ห้องอาหาร)", 
    "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", 
    "ประเภท 4",
    "ประเภท 5 ไม่เป็นโรงแรม"
]

# ตัวเลือกสถานะค่าธรรมเนียม
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

def load_data():
    conn = get_connection()
    query = """
        SELECT 
            h.id AS 'รหัสระบบ',
            l.license_no AS 'เลขที่ใบอนุญาต (ร.บ.2)',
            h.hotel_name AS 'ชื่อโรงแรม',
            h.hotel_type AS 'ประเภทโรงแรม',
            h.owner_name AS 'ชื่อผู้ประกอบการ',
            h.manager_name AS 'ชื่อผู้จัดการโรงแรม (หน้างาน)',
            h.total_rooms AS 'จำนวนห้องพัก',
            l.issue_date AS 'วันออกใบอนุญาต',
            l.expiry_date AS 'วันหมดอายุ',
            l.fee_status AS 'สถานะค่าธรรมเนียมรายปี',
            h.address AS 'ที่อยู่',
            h.tel AS 'เบอร์โทรศัพท์เจ้าของ',
            h.manager_tel AS 'เบอร์โทรศัพท์ผู้จัดการ'
        FROM hotels h
        LEFT JOIN licenses l ON h.id = l.hotel_id
        ORDER BY l.license_no ASC
    """
    try:
        df = pd.read_sql(query, con=conn)
        return df
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def delete_hotel(hotel_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM hotels WHERE id = ?", (hotel_id,))
        cursor.execute("DELETE FROM licenses WHERE hotel_id = ?", (hotel_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {e}")
        return False
    finally:
        conn.close()

def to_excel(df_data):
    df_excel = df_data.copy()
    for col in df_excel.columns:
        if df_excel[col].dtype == 'object':
            df_excel[col] = df_excel[col].astype(str)
            
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='รายงานทะเบียนโรงแรม')
    except:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='รายงานทะเบียนโรงแรม')
            
    processed_data = output.getvalue()
    return processed_data

# 3. เมนูแยกแท็บใช้งาน
