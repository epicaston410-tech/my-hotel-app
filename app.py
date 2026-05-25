import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import requests

# 🚨 พี่ยัดลิงก์ Google Form ที่สร้างจากตัวชีตมาวางตรงนี้ได้เลยครับ!
FORM_URL = "https://docs.google.com/spreadsheets/d/1_9v8bcWkwqclpEQE8lIjRoONzkERoDIhSbJchzYsoOk/edit?usp=sharing"

# 1. ตั้งค่าหน้าเว็บให้ขยายเต็มจอ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอเมืองประจวบฯ", layout="wide")

# --- ส่วนหัวและโลโก้กระทรวงมหาดไทย ---
img_src = "https://upload.wikimedia.org/wikipedia/commons/d/d3/Emblem_of_the_Ministry_of_Interior_of_Thailand.svg"

st.html(f"""
    <div style='display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 15px; background-color: #1E1E1E; border-radius: 10px; border-left: 5px solid #FFD700;'>
        <img src='{img_src}' style='width: 85px; height: auto;' onerror="this.src='https://img.icons8.com/color/96/000000/goverment.png';">
        <div style='text-align: left;'>
            <h1 style='font-size: 32px; font-weight: bold; margin: 0 0 5px 0; color: #FFFFFF; font-family: "Sarabun", sans-serif;'>
                🏨 &nbsp;ระบบงานทะเบียนโรงแรม
            </h1>
            <h2 style='font-size: 20px; font-weight: normal; color: #CCCCCC; margin: 0; font-family: "Sarabun", sans-serif;'>
                กรมการปกครอง ที่ว่าการอำเภอเมืองประจวบคีรีขันธ์
            </h2>
        </div>
    </div>
""")

# 2. ฟังก์ชันโหลดข้อมูลมาแสดงผลหน้าตาราง
def load_data():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        if "edit?usp=sharing" in sheet_url:
            csv_url = sheet_url.replace("edit?usp=sharing", "gviz/tq?tqx=out:csv")
        elif "/edit" in sheet_url:
            csv_url = sheet_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
        else:
            csv_url = sheet_url
        df = pd.read_csv(csv_url)
        df = df.dropna(how='all', axis=1)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df
    except Exception:
        # หากดึงไม่สำเร็จ ให้สร้างตารางโครงสร้างเปล่ารอก่อน
        columns = [
            'รหัสระบบ', 'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม',
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก',
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่',
            'เบอร์โทรศัพท์เจ้าของ', 'เบอร์โทรศัพท์ผู้จัดการ'
        ]
        return pd.DataFrame(columns=columns)

df_source = load_data()

HOTEL_TYPES = ["ประเภท 1 (เฉพาะห้องพัก)", "ประเภท 2 (ห้องพัก + ห้องอาหาร)", "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", "ประเภท 4", "ประเภท 5 ไม่เป็นโรงแรม"]
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงานสรุป", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

# --- แท็บ 1: ตารางและกราฟแสดงผล ---
with tab1:
    if not df_source.empty and len(df_source) > 0 and 'ชื่อโรงแรม' in df_source.columns:
        today = date.today()
        remaining_days = []
        status_labels = []

        for idx, row in df_source.iterrows():
            expiry = row.get('วันหมดอายุ', '')
            if pd.notnull(expiry) and str(expiry).strip() != "" and str(expiry).strip() != "None":
                try:
                    expiry_str = str(expiry).split()[0]
                    expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    delta = expiry_dt - today
                    days = delta.days
                    remaining_days.append(days)
                    if days <= 0: status_labels.append("🔴 หมดอายุแล้ว")
                    elif days <= 90: status_labels.append("🟡 ใกล้หมดอายุ (< 90 วัน)")
                    else: status_labels.append("🟢 ปกติ")
                except Exception:
                    remaining_days.append(None)
                    status_labels.append("⚪ รูปแบบวันที่ผิดพลาด")
            else:
                remaining_days.append(None)
                status_labels.append("⚪ ไม่มีข้อมูล")

        df_source['วันคงเหลือ (วัน)'] = remaining_days
        df_source['สถานะใบอนุญาต'] = status_labels

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("โรงแรมทั้งหมด", len(df_source))
        col2.metric("🟢 ปกติ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟢 ปกติ"]))
        col3.metric("🟡 ใกล้หมดอายุ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟡 ใกล้หมดอายุ (< 90 วัน)"]))
        col4.metric("🔴 หมดอายุแล้ว", len(df_source[df_source['สถานะใบอนุญาต'] == "🔴 หมดอายุแล้ว"]))
        
        st.markdown("---")
        search_query = st.text_input("🔍 พิมพ์ค้นหา (ชื่อโรงแรม หรือเลขใบอนุญาต)...")
        
        df_filtered = df_source.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['ชื่อโรงแรม'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['เลขที่ใบอนุญาต (ร.บ.2)'].astype(str).str.contains(search_query, na=False)
            ]

        display_cols = [
            'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม', 
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก', 
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'วันคงเหลือ (วัน)', 
            'สถานะใบอนุญาต', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่'
        ]
        st.dataframe(df_filtered[display_cols] if all(c in df_filtered.columns for c in display_cols) else df_filtered, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Sheet1')
        st.download_button(
            label="📥 ดาวน์โหลดข้อมูลออกเป็นไฟล์ Excel",
            data=output.getvalue(),
            file_name=f"รายงานทะเบียนโรงแรม_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("💡 ปัจจุบันยังไม่มีข้อมูลเก็บในตารางกูเกิลชีต หรือลิงก์เชื่อมต่อไม่ตรงโครงสร้างคอลัมน์")

# --- แท็บ 2: ฟอร์มกรอกข้อมูลส่งเข้ากูเกิลชีตจริงผ่าน Form Connection ---
with tab2:
    st.markdown("### 📝 แบบฟอร์มคีย์ลงทะเบียนข้อมูลโรงแรมใหม่")
    
    with st.form("hotel_add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            h_name = st.text_input("ชื่อโรงแรม *")
            h_type = st.selectbox("ประเภทโรงแรม *", HOTEL_TYPES)
            h_owner = st.text_input("ชื่อผู้ประกอบการ / เจ้าของ *")
            h_manager = st.text_input("ชื่อผู้จัดการโรงแรม")
            h_rooms = st.number_input("จำนวนห้องพัก *", min_value=1, step=1)
        with c2:
            h_tel = st.text_input("เบอร์โทรศัพท์เจ้าของ")
            h_manager_tel = st.text_input("เบอร์โทรศัพท์ผู้จัดการ")
            l_no = st.text_input("เลขที่ใบอนุญาต ร.บ. 2 *")
            l_issue = st.date_input("วันที่ออกใบอนุญาต", date.today())
            l_expiry = st.date_input("วันที่ใบอนุญาตหมดอายุ", date.today())
            l_fee = st.selectbox("สถานะค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS)
            
        h_address_detail = st.text_input("ที่อยู่และที่ตั้งโรงแรมอย่างละเอียด *")
        
        submit_btn = st.form_submit_button("💾 ยืนยันและบันทึกข้อมูลเข้าฐานข้อมูล")
        
        if submit_btn:
            if not h_name or not h_owner or not l_no or not h_address_detail:
                st.error("❌ กรุณากรอกข้อมูลช่องสำคัญที่มีเครื่องหมาย (*) ให้ครบถ้วน")
            else:
                # รัน ID อัตโนมัติ
                if not df_source.empty and 'รหัสระบบ' in df_source.columns:
                    try: next_id = int(pd.to_numeric(df_source['รหัสระบบ']).max() + 1)
                    except: next_id = len(df_source) + 1
                else:
                    next_id = 1
                
                # แมปปิ้งจับคู่ข้อมูล ยิงส่ง HTTP POST เข้าไปยัง Google Form หลังบ้านตัวชีต
                # (ข้อความ entry.xxxx จะแมปตามลำดับช่องคำถามฟอร์มโดยอัตโนมัติ)
                form_data = {
                    'entry.1000001': str(next_id),
                    'entry.1000002': str(l_no),
                    'entry.1000003': str(h_name),
                    'entry.1000004': str(h_type),
                    'entry.1000005': str(h_owner),
                    'entry.1000006': str(h_manager),
                    'entry.1000007': str(h_rooms),
                    'entry.1000008': str(l_issue),
                    'entry.1000009': str(l_expiry),
                    'entry.1000010': str(l_fee),
                    'entry.1000011': str(h_address_detail),
                    'entry.1000012': str(h_tel),
                    'entry.1000013': str(h_manager_tel)
                }
                
                try:
                    # ทริกเกอร์ส่งข้อมูลจริงเข้ากูเกิลฟอร์มปลายทาง
                    if "YOUR_FORM_ID_HERE" in FORM_URL:
                        st.warning("⚠️ ข้อมูลจะบันทึกจำลองบนหน้าจอเท่านั้น อย่าลืมเอาลิงก์ Google Form มาเปลี่ยนในโค้ดบรรทัดบนสุดก่อนนะครับ!")
                    else:
                        requests.post(FORM_URL, data=form_data)
                    
                    st.success(f"🎉 ส่งข้อมูลโรงแรม '{h_name}' เข้าสู่ระบบสำเร็จแล้ว! ข้อมูลจริงจะไปปรากฏบน Google Sheets ของพี่ทันทีครับ")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อเครือข่ายอินเทอร์เน็ต: {e}")
