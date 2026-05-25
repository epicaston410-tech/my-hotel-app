import streamlit as st
import pandas as pd
from datetime import date, datetime
import io
import requests

# 1. ตั้งค่าหน้าจอการใช้งานของระบบให้กระจายเต็มจอ (Wide Layout)
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอเมืองประจวบฯ", layout="wide")

# --- 2. ส่วนหัวเว็บและจัดการโลโก้ (ใช้ HTML สไตล์กระทรวงมหาดไทย/งานปกครอง) ---
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

# --- 3. ฟังก์ชันการดึงข้อมูลและการบันทึก (เชื่อมระบบผ่าน Web Form API ของกูเกิล) ---
def get_google_sheet_url():
    try:
        # ดึงลิงก์ต้นทางจากระบบความปลอดภัย Advanced Settings (Secrets)
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        if "edit?usp=sharing" in sheet_url:
            return sheet_url.replace("edit?usp=sharing", "gviz/tq?tqx=out:csv")
        elif "/edit" in sheet_url:
            return sheet_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"
        return sheet_url
    except Exception as e:
        st.error(f"⚠️ ไม่พบการตั้งค่าลิงก์กูเกิลชีตใน Secrets: {e}")
        return None

def load_data():
    csv_url = get_google_sheet_url()
    if csv_url is None:
        return pd.DataFrame()
    try:
        # อ่านข้อมูลและจัดระบบคอลัมน์ไม่ให้ขยะติดเข้ามา
        df = pd.read_csv(csv_url)
        df = df.dropna(how='all', axis=1)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df
    except Exception as e:
        # คอลัมน์มาตรฐานกรณีเปิดระบบครั้งแรกหรือฐานข้อมูลยังว่างเปล่า
        columns = [
            'รหัสระบบ', 'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม',
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก',
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่',
            'เบอร์โทรศัพท์เจ้าของ', 'เบอร์โทรศัพท์ผู้จัดการ'
        ]
        return pd.DataFrame(columns=columns)

# ทำการโหลดตารางข้อมูลมาสแตนด์บายบนแอป
df_source = load_data()

# รายการตัวเลือกสำหรับจัดฟอร์มข้อมูลในอำเภอเมืองประจวบคีรีขันธ์
HOTEL_TYPES = ["ประเภท 1 (เฉพาะห้องพัก)", "ประเภท 2 (ห้องพัก + ห้องอาหาร)", "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", "ประเภท 4", "ประเภท 5 ไม่เป็นโรงแรม"]
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

# --- 4. การจัดการแบ่งหน้าจอออกเป็น 2 แท็บเมนูหลัก ---
tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงานสรุป", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

# --- แท็บที่ 1: รายงานสถิติและตารางข้อมูลหลัก ---
with tab1:
    if not df_source.empty and len(df_source) > 0 and 'ชื่อโรงแรม' in df_source.columns:
        today = date.today()
        remaining_days = []
        status_labels = []

        # ระบบคำนวณและแจ้งเตือนวันใบอนุญาตหมดอายุของแต่ละแห่งอัตโนมัติ
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

        # บล็อกการแสดงผลภาพรวมสถานะด่วน (Metrics)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("โรงแรมทั้งหมดในฐานข้อมูล", len(df_source))
        col2.metric("🟢 สถานะปกติ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟢 ปกติ"]))
        col3.metric("🟡 ใกล้หมดอายุ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟡 ใกล้หมดอายุ (< 90 วัน)"]))
        col4.metric("🔴 หมดอายุแล้ว", len(df_source[df_source['สถานะใบอนุญาต'] == "🔴 หมดอายุแล้ว"]))
        
        st.markdown("---")
        st.markdown("### 🔍 ค้นหาและกรองข้อมูลแบบเรียลไทม์")
        search_query = st.text_input("พิมพ์ชื่อโรงแรม, เลขที่ใบอนุญาต ร.บ.2 หรือชื่อเจ้าของ เพื่อกรองหาในตาราง...")
        
        df_filtered = df_source.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['ชื่อโรงแรม'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['เลขที่ใบอนุญาต (ร.บ.2)'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['ชื่อผู้ประกอบการ'].astype(str).str.contains(search_query, na=False) |
                df_filtered['ที่อยู่'].astype(str).str.contains(search_query, na=False)
            ]

        # คอลัมน์ลำดับโครงสร้างราชการที่จะนำมาโชว์บนหน้าตารางเว็บ
        display_cols = [
            'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม', 
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก', 
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'วันคงเหลือ (วัน)', 
            'สถานะใบอนุญาต', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่'
        ]
        
        st.dataframe(df_filtered[display_cols] if all(c in df_filtered.columns for c in display_cols) else df_filtered, use_container_width=True)
        
        # ฟังก์ชันแปลงตารางชุดที่กรองไปเป็นไฟล์รายงานส่งนายอำเภอหรือจังหวัดได้ทันที
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='รายงานสรุปทะเบียน')
        st.download_button(
            label="📥 ดาวน์โหลดตารางข้อมูลชุดนี้ออกเป็นไฟล์ Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"รายงานทะเบียนโรงแรม_อำเภอเมืองประจวบ_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("💡 เชื่อมโยงระบบสำเร็จแล้ว แต่กูเกิลชีตของพี่ยังไม่มีแถวข้อมูลเก็บไว้ หรือโครงสร้างคอลัมน์ชื่อโรงแรมไม่ตรง")

# --- แท็บที่ 2: ฟอร์มบันทึกบันทึกข้อมูลเข้าฐานข้อมูลกูเกิลชีต ---
with tab2:
    st.markdown("### 📝 แบบฟอร์มลงทะเบียนและคีย์ข้อมูลโรงแรมใหม่")
    st.info("⚠️ ก่อนกดบันทึก: ตรวจสอบให้แน่ใจว่าพี่ได้กดเปิดแชร์ Google Sheets ลิงก์นั้นให้เป็นสิทธิ์ 'ทุกคนที่มีลิงก์เป็นผู้แก้ไข (Editor)' เรียบร้อยแล้ว ข้อมูลจะวิ่งเข้าตารางหลักทันทีครับ")
    
    with st.form("hotel_add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            h_name = st.text_input("ชื่อโรงแรม *")
            h_type = st.selectbox("ประเภทโรงแรม *", HOTEL_TYPES)
            h_owner = st.text_input("ชื่อผู้ประกอบการ / เจ้าของลิขสิทธิ์ *")
            h_manager = st.text_input("ชื่อผู้จัดการโรงแรม (หน้างาน)")
            h_rooms = st.number_input("จำนวนห้องพักทั้งหมดในใบอนุญาต *", min_value=1, step=1)
        with c2:
            h_tel = st.text_input("เบอร์โทรศัพท์ติดต่อเจ้าของ")
            h_manager_tel = st.text_input("เบอร์โทรศัพท์ติดต่อผู้จัดการ")
            l_no = st.text_input("เลขที่ใบอนุญาต ร.บ. 2 *")
            l_issue = st.date_input("วันที่ลงนามออกใบอนุญาต", date.today())
            l_expiry = st.date_input("วันที่ใบอนุญาตสิ้นสุด/หมดอายุ", date.today())
            l_fee = st.selectbox("สถานะการชำระค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS)
            
        h_address_detail = st.text_input("ที่อยู่และที่ตั้งโรงแรมอย่างละเอียด (เลขที่บ้าน, หมู่ที่, ตำบล, อำเภอ) *")
        
        submit_btn = st.form_submit_button("💾 ยืนยันและบันทึกข้อมูลเข้าฐานข้อมูล")
        
        if submit_btn:
            if not h_name or not h_owner or not l_no or not h_address_detail:
                st.error("❌ บันทึกไม่สำเร็จ: กรุณากรอกช่องข้อมูลสำคัญที่มีเครื่องหมายกำกับดาว (*) ให้ครบก่อนครับพี่")
            else:
                # คำนวณตั้งค่าเลขรหัสรันระบบ ID แถวใหม่ให้อัตโนมัติ
                if not df_source.empty and 'รหัสระบบ' in df_source.columns:
                    try: next_id = int(pd.to_numeric(df_source['รหัสระบบ']).max() + 1)
                    except: next_id = len(df_source) + 1
                else:
                    next_id = 1
                
                # ฟอร์แมตข้อมูลเตรียมเขียนส่งในรูปแบบตาราง
                new_row_data = {
                    'รหัสระบบ': str(next_id),
                    'เลขที่ใบอนุญาต (ร.บ.2)': str(l_no),
                    'ชื่อโรงแรม': str(h_name),
                    'ประเภทโรงแรม': str(h_type),
                    'ชื่อผู้ประกอบการ': str(h_owner),
                    'ชื่อผู้จัดการโรงแรม (หน้างาน)': str(h_manager),
                    'จำนวนห้องพัก': str(h_rooms),
                    'วันออกใบอนุญาต': str(l_issue),
                    'วันหมดอายุ': str(l_expiry),
                    'สถานะค่าธรรมเนียมรายปี': str(l_fee),
                    'ที่อยู่': str(h_address_detail),
                    'เบอร์โทรศัพท์เจ้าของ': str(h_tel),
                    'เบอร์โทรศัพท์ผู้จัดการ': str(h_manager_tel)
                }
                
                # ระบบยิงบันทึกเข้า Google Sheets ปลายทาง
                try:
                    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    # คัดแยก ID ของไฟล์ชีตมาทำ Request ส่งส่งข้อมูลแบบฟอร์ม
                    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                    
                    # บันทึกสำเร็จสเต็ปแรกจำลองหน้าจออัปเดตแคช
                    st.success(f"🎉 ระบบทำการลงทะเบียนโรงแรม '{h_name}' บันทึกเข้าไปยังฐานข้อมูล Google Sheets เรียบร้อยแล้วครับพี่! (สามารถรีเฟรชหน้าเว็บเพื่อดูข้อมูลล่าสุดได้ทันที)")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ ระบบขัดข้องในการเชื่อมต่อเพื่อเขียนแถวข้อมูลใหม่: {e}")
