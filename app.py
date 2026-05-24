import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import io

# 1. ตั้งค่าหน้าเว็บให้ดูสะอาด สไตล์งานราชการ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอ", layout="wide")

st.title("🏨 ระบบบริหารจัดการทะเบียนและแจ้งเตือนวันหมดอายุโรงแรม")
st.subheader("งานทะเบียนและฝ่ายความมั่นคง ที่ว่าการอำเภอ")
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

# เพิ่มตัวเลือกประเภทโรงแรม (เพิ่ม ประเภท 5)
HOTEL_TYPES = [
    "ประเภท 1 (เฉพาะห้องพัก)", 
    "ประเภท 2 (ห้องพัก + ห้องอาหาร)", 
    "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", 
    "ประเภท 4",
    "ประเภท 5 ไม่เป็นโรงแรม"
]

# เพิ่มตัวเลือกสถานะค่าธรรมเนียม (เพิ่ม ไม่มีค่าธรรมเนียม)
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

def load_data():
    conn = get_connection()
    # ดึงข้อมูลพร้อมตั้งชื่อคอลัมน์ภาษาไทยให้ชัดเจน และดึงคอลัมน์ดิบมาเก็บไว้ตรวจสอบด้วย
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
    # ใช้ engine='openpyxl' (หากมีปัญหาตัวนี้ระบบจะไม่ค้าง)
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='รายงานทะเบียนโรงแรม')
    except:
        # Fallback ในกรณีที่สตรีมลิตคลาวด์ยังอัปเดตไฟล์ก้อนแพ็กเกจไม่เสร็จ
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_excel.to_excel(writer, index=False, sheet_name='รายงานทะเบียนโรงแรม')
            
    processed_data = output.getvalue()
    return processed_data

# 3. เมนูแยกแท็บใช้งาน
tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงาน", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

with tab1:
    df_source = load_data()
    if not df_source.empty:
        today = date.today()
        remaining_days = []
        status_labels = []

        for idx, row in df_source.iterrows():
            expiry = row['วันหมดอายุ']
            if pd.notnull(expiry) and expiry != "":
                try:
                    if isinstance(expiry, str):
                        expiry_dt = datetime.strptime(expiry.split()[0], "%Y-%m-%d").date()
                    else:
                        expiry_dt = expiry
                        
                    delta = expiry_dt - today
                    days = delta.days
                    remaining_days.append(days)
                    
                    if days <= 0:
                        status_labels.append("🔴 หมดอายุแล้ว")
                    elif days <= 90:
                        status_labels.append("🟡 ใกล้หมดอายุ (น้อยกว่า 90 วัน)")
                    else:
                        status_labels.append("🟢 ปกติ")
                except Exception:
                    remaining_days.append(None)
                    status_labels.append("⚪ รูปแบบวันที่ไม่ถูกต้อง")
            else:
                remaining_days.append(None)
                status_labels.append("⚪ ไม่มีข้อมูลใบอนุญาต")

        df_source['วันคงเหลือ (วัน)'] = remaining_days
        df_source['สถานะใบอนุญาต'] = status_labels

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("โรงแรมทั้งหมดในอำเภอ", len(df_source))
        col2.metric("🟢 Status ปกติ", len(df_source[df_source['App Status'] == "🟢 ปกติ" if 'App Status' in df_source else df_source['สถานะใบอนุญาต'] == "🟢 ปกติ"]))
        col3.metric("🟡 ใกล้หมดอายุ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟡 ใกล้หมดอายุ (น้อยกว่า 90 วัน)"]))
        col4.metric("🔴 หมดอายุแล้ว", len(df_source[df_source['สถานะใบอนุญาต'] == "🔴 หมดอายุแล้ว"]))
        
        st.markdown("---")

        st.markdown("### 🔍 ค้นหาข้อมูลโรงแรม")
        search_query = st.text_input("พิมพ์ชื่อโรงแรม, เลขใบอนุญาต, ชื่อผู้จัดการ หรือชื่อตำบล เพื่อค้นหา...")
        
        df_filtered = df_source.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['ชื่อโรงแรม'].str.contains(search_query, na=False) | 
                df_filtered['เลขที่ใบอนุญาต (ร.บ.2)'].str.contains(search_query, na=False) | 
                df_filtered['ชื่อผู้ประกอบการ'].str.contains(search_query, na=False) |
                df_filtered['ชื่อผู้จัดการโรงแรม (หน้างาน)'].str.contains(search_query, na=False) |
                df_filtered['ที่อยู่'].str.contains(search_query, na=False)
            ]

        st.markdown("### 📋 ตารางข้อมูลสถานะล่าสุด")
        
        # เงื่อนไขสลับเบอร์ติดต่ออัตโนมัติป้องกันช่องว่าง
        contact_phones = []
        for idx, row in df_filtered.iterrows():
            m_tel = row['เบอร์โทรศัพท์ผู้จัดการ']
            o_tel = row['เบอร์โทรศัพท์เจ้าของ']
            m_name = row['ชื่อผู้จัดการโรงแรม (หน้างาน)']
            
            if pd.isnull(m_name) or str(m_name).strip() == "" or pd.isnull(m_tel) or str(m_tel).strip() == "":
                contact_phones.append(o_tel if (pd.notnull(o_tel) and str(o_tel).strip() != "") else "-")
            else:
                contact_phones.append(m_tel)
                
        df_filtered['เบอร์โทรติดต่อหน้างาน'] = contact_phones

        # จัดระเบียบลำดับคอลัมน์หน้าจอ
        display_cols = [
            'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม', 
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก', 
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'วันคงเหลือ (วัน)', 
            'สถานะใบอนุญาต', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่', 'เบอร์โทรติดต่อหน้างาน'
        ]
        
        items_per_page = 20
        total_items = len(df_filtered)
        
        if total_items > 0:
            import math
            total_pages = math.ceil(total_items / items_per_page)
            
            if 'current_page' not in st.session_state:
                st.session_state.current_page = 1
                
            if st.session_state.current_page > total_pages:
                st.session_state.current_page = total_pages
            if st.session_state.current_page < 1:
                st.session_state.current_page = 1

            start_idx = (st.session_state.current_page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_items)
            
            df_page = df_filtered.iloc[start_idx:end_idx]
            st.dataframe(df_page[display_cols], use_container_width=True)
            
            p_col1, p_col2, p_col3, p_col4 = st.columns([2, 3, 2, 5])
            with p_col1:
                if st.button("⬅️ หน้าก่อนหน้า", disabled=(st.session_state.current_page == 1)):
                    st.session_state.current_page -= 1
                    st.rerun()
            with p_col2:
                page_options = list(range(1, total_pages + 1))
                selected_page = st.selectbox(
                    f"แสดงผลโรงแรมลำดับที่ {start_idx + 1} - {end_idx} (จากทั้งหมด {total_items} โรงแรม)",
                    options=page_options,
                    index=page_options.index(st.session_state.current_page),
                    key="page_select_box"
                )
                if selected_page != st.session_state.current_page:
                    st.session_state.current_page = selected_page
                    st.rerun()
            with p_col3:
                if st.button("หน้าถัดไป ➡️", disabled=(st.session_state.current_page == total_pages)):
                    st.session_state.current_page += 1
                    st.rerun()
        else:
            st.warning("❌ ไม่พบข้อมูลโรงแรมที่ตรงกับเงื่อนไขการค้นหา")
            
        st.markdown("---")
        
        st.markdown("### ⚙️ จัดการข้อมูลการจัดการระดับโรงแรม (แก้ไข/ลบข้อมูล)")
        hotel_list = {f"[{row['รหัสระบบ']}] ใบอนุญาต: {row['เลขที่ใบอนุญาต (ร.บ.2)']} - {row['ชื่อโรงแรม']}": row['รหัสระบบ'] for idx, row in df_filtered.iterrows()}
        selected_hotel_str = st.selectbox("เลือกโรงแรมที่ต้องการจัดการข้อมูล:", ["-- กรุณาเลือกโรงแรม --"] + list(hotel_list.keys()))
        
        if selected_hotel_str != "-- กรุณาเลือกโรงแรม --":
            selected_id = hotel_list[selected_hotel_str]
            hotel_row = df_filtered[df_filtered['รหัสระบบ'] == selected_id].iloc[0]
            
            edit_col, delete_col = st.columns([2, 1])
            with edit_col:
                st.info(f"📝 ฟอร์มแก้ไขข้อมูล: {hotel_row['ชื่อโรงแรม']}")
                
                # บั๊กเดิมเกิดจากปุ่ม Submit ผิดตำแหน่ง และคีย์ชื่อคอลัมน์ไม่ตรง
                with st.form(f"edit_form_{selected_id}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_name = st.text_input("ชื่อโรงแรม *", value=str(hotel_row['ชื่อโรงแรม']))
                        
                        try: default_type_idx = HOTEL_TYPES.index(hotel_row['ประเภทโรงแรม'])
                        except: default_type_idx = 0
                        edit_type = st.selectbox("ประเภทโรงแรม *", HOTEL_TYPES, index=default_type_idx)
                        
                        edit_owner = st.text_input("ชื่อผู้ประกอบการ / เจ้าของ *", value=str(hotel_row['ชื่อผู้ประกอบการ']))
                        edit_manager = st.text_input("ชื่อผู้จัดการโรงแรม (หน้างาน)", value=str(hotel_row['ชื่อผู้จัดการโรงแรม (หน้างาน)']) if hotel_row['ชื่อผู้จัดการโรงแรม (หน้างาน)'] and str(hotel_row['ชื่อผู้จัดการโรงแรม (หน้างาน)']) != 'None' else "")
                        edit_rooms = st.number_input("จำนวนห้องพักทั้งหมด *", min_value=1, step=1, value=int(hotel_row['จำนวนห้องพัก']))
                    
                    with ec2:
                        # 🔎 แก้ไขบั๊กคอลัมน์ชื่อตรงนี้ให้ถูกต้องตรงกับที่ SELECT (เบอร์โทรศัพท์เจ้าของ / เบอร์โทรศัพท์ผู้จัดการ)
                        edit_tel = st.text_input("เบอร์โทรศัพท์เจ้าของ", value=str(hotel_row['เบอร์โทรศัพท์เจ้าของ']) if hotel_row['เบอร์โทรศัพท์เจ้าของ'] and str(hotel_row['เบอร์โทรศัพท์เจ้าของ']) != 'None' else "")
                        edit_manager_tel = st.
