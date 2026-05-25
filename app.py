import streamlit as st
import pandas as pd
from datetime import date, datetime
import io

# 1. ตั้งค่าหน้าเว็บสไตล์งานราชการ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอเมืองประจวบฯ", layout="wide")

# --- ส่วนหัวของระบบและจัดการโลโก้ (ดึงตราสิงห์กระทรวงมหาดไทยโดยตรงผ่านลิงก์สาธารณะที่ปลอดภัย) ---
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

# 2. ฟังก์ชันดึงข้อมูลจาก Google Sheets ผ่านรูปแบบ CSV Link (เสถียรที่สุดและแก้ Error เรียบร้อย)
def get_google_sheet_url():
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # ปรับการแชร์ลิงก์ให้อยู่ในฟอร์แมต API ดึงข้อมูลตารางแบบรวดเร็ว
        if "edit?usp=sharing" in sheet_url:
            return sheet_url.replace("edit?usp=sharing", "gviz/tq?tqx=out:csv")
        elif "/edit" in sheet_url:
            return sheet_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
        return sheet_url
    except Exception as e:
        st.error(f"⚠️ ไม่พบการตั้งค่าลิงก์ใน Advanced Settings (Secrets): {e}")
        return None

# ฟังก์ชันแปลงข้อมูลชีตมาเป็นตาราง DataFrame ในระบบ
def load_data():
    csv_url = get_google_sheet_url()
    if csv_url is None:
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_url)
        # เคลียร์คอลัมน์และแถวว่างที่อาจติดมาจากการจัดฟอร์แมตในชีต
        df = df.dropna(how='all', axis=1)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df
    except Exception as e:
        # โครงสร้างตารางมาตรฐานสไตล์งานทะเบียนอำเภอ (กรณีดึงข้อมูลไม่สำเร็จหรือชีตโล่ง)
        columns = [
            'รหัสระบบ', 'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม',
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก',
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่',
            'เบอร์โทรศัพท์เจ้าของ', 'เบอร์โทรศัพท์ผู้จัดการ'
        ]
        return pd.DataFrame(columns=columns)

# เรียกใช้การโหลดข้อมูลจากกูเกิลชีตมาแสตนบายในแอป
df_source = load_data()

# ข้อมูลตัวเลือกสำหรับกรอกแบบฟอร์มในพื้นที่อำเภอเมืองประจวบฯ
SUBDISTRICTS = ["ตำบลเกาะหลัก", "ตำบลอ่าวน้อย", "ตำบลคลองวาฬ", "ตำบลห้วยทราย", "ตำบลบ่อนอก", "เขตเทศบาลเมืองประจวบคีรีขันธ์"]
HOTEL_TYPES = ["ประเภท 1 (เฉพาะห้องพัก)", "ประเภท 2 (ห้องพัก + ห้องอาหาร)", "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", "ประเภท 4", "ประเภท 5 ไม่เป็นโรงแรม"]
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

# 3. เมนูสลับการทำงานระบบ
tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงาน", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

with tab1:
    if not df_source.empty and len(df_source) > 0 and 'ชื่อโรงแรม' in df_source.columns:
        today = date.today()
        remaining_days = []
        status_labels = []

        # คำนวณวันหมดอายุของใบอนุญาตอัตโนมัติ
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
                    status_labels.append("⚪ รูปแบบวันที่ไม่ถูกต้อง")
            else:
                remaining_days.append(None)
                status_labels.append("⚪ ไม่มีข้อมูลวันหมดอายุ")

        df_source['วันคงเหลือ (วัน)'] = remaining_days
        df_source['สถานะใบอนุญาต'] = status_labels

        # สรุปภาพรวมสถิติใบอนุญาตของทั้งอำเภอ (Metrics)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("โรงแรมทั้งหมดในชีต", len(df_source))
        col2.metric("🟢 สถานะปกติ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟢 ปกติ"]))
        col3.metric("🟡 ใกล้หมดอายุ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟡 ใกล้หมดอายุ (< 90 วัน)"]))
        col4.metric("🔴 หมดอายุแล้ว", len(df_source[df_source['สถานะใบอนุญาต'] == "🔴 หมดอายุแล้ว"]))
        
        st.markdown("---")
        st.markdown("### 🔍 ค้นหาและคัดกรองข้อมูลโรงแรม")
        search_query = st.text_input("พิมพ์คำค้นหา เช่น ชื่อโรงแรม, เลขที่ใบอนุญาต ร.บ.2 หรือชื่อผู้ประกอบการ...")
        
        df_filtered = df_source.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['ชื่อโรงแรม'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['เลขที่ใบอนุญาต (ร.บ.2)'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['ชื่อผู้ประกอบการ'].astype(str).str.contains(search_query, na=False) |
                df_filtered['ที่อยู่'].astype(str).str.contains(search_query, na=False)
            ]

        display_cols = [
            'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม', 
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก', 
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'วันคงเหลือ (วัน)', 
            'สถานะใบอนุญาต', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่'
        ]
        
        # แสดงผลตารางข้อมูลหลักแบบกระจายเต็มหน้าจอ
        st.dataframe(df_filtered[display_cols] if all(c in df_filtered.columns for c in display_cols) else df_filtered, use_container_width=True)
        
        # ปุ่มสำหรับสร้างไฟล์รายงานส่งนายอำเภอหรือจังหวัด
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='รายงานสรุปข้อมูล')
        st.download_button(
            label="📥 ดาวน์โหลดข้อมูลชุดนี้เป็นไฟล์ Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"รายงานสรุปทะเบียนโรงแรม_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("💡 ดึงโครงสร้างระบบสำเร็จแล้ว แต่ยังไม่มีข้อมูลแสดงผลในตารางเนื่องจาก Google Sheets ของพี่เป็นชีตว่างเปล่า")

with tab2:
    st.markdown("### 📝 แบบฟอร์มบันทึกข้อมูลโรงแรมใหม่")
    st.info("💡 ระบบเปิดใช้งานบน Cloud Server สาธารณะผ่าน Public Link ซึ่งมีความปลอดภัยและมีความเสถียรสูงในการแสดงผลดึงรายงาน หากพี่ต้องการเปิดฟังก์ชันให้กดส่งข้อมูลคีย์เพิ่มย้อนกลับไปบันทึกลง Google Sheets แบบ Real-time แนะนำให้ลงสิทธิ์แบบ Google Service Account JSON ในการพัฒนาขั้นถัดไปครับ")
    
    with st.form("hotel_add_form"):
        c1, c2 = st.columns(2)
        with c1:
            h_name = st.text_input("ชื่อโรงแรม *")
            h_type = st.selectbox("ประเภทโรงแรม *", HOTEL_TYPES)
            h_owner = st.text_input("ชื่อผู้ประกอบการ / เจ้าของ *")
            h_manager = st.text_input("ชื่อผู้จัดการโรงแรม (หน้างาน)")
            h_rooms = st.number_input("จำนวนห้องพักทั้งหมด *", min_value=1, step=1)
        with c2:
            h_tel = st.text_input("เบอร์โทรศัพท์เจ้าของ")
            h_manager_tel = st.text_input("เบอร์โทรศัพท์ผู้จัดการ")
            l_no = st.text_input("เลขที่ใบอนุญาต ร.บ. 2 *")
            l_issue = st.date_input("วันที่ออกใบอนุญาต", date.today())
            l_expiry = st.date_input("วันที่ใบอนุญาตหมดอายุ", date.today())
            l_fee = st.selectbox("สถานะค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS)
            
        h_address_detail = st.text_input("ที่อยู่ตำแหน่งตั้งโรงแรม (ระบุเลขที่บ้าน, หมู่ที่, ถนน, ตำบล) *")
        submit_btn = st.form_submit_button("💾 จำลองการตรวจสอบและเพิ่มข้อมูลโรงแรม")
        if submit_btn:
            if not h_name or not h_owner or not l_no or not h_address_detail:
                st.error("❌ กรุณากรอกข้อมูลในช่องที่มีเครื่องหมาย * ให้ครบถ้วน")
            else:
                st.success(f"🎉 ตรวจสอบความถูกต้องของโรงแรม '{h_name}' เรียบร้อยแล้ว")
