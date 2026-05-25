import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime
import io
import os

# 1. ตั้งค่าหน้าเว็บสไตล์งานราชการ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอ (Google Sheets)", layout="wide")

# --- ส่วนหัวของระบบและจัดการโลโก้ ---
def get_image_base64(image_name):
    import base64
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "static", image_name)
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

img_base64 = get_image_base64("dopa.png")
if img_base64:
    img_src = f"data:image/png;base64,{img_base64}"
else:
    img_src = "https://raw.githubusercontent.com/streamlit/proactive-connectors/main/branding/logo.png"

st.html(f"""
    <div style='display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 10px;'>
        <img src='{img_src}' style='width: 100px; height: auto;' onerror="this.src='https://img.icons8.com/color/96/000000/goverment.png';">
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

# 2. เชื่อมต่อ Google Sheets หลังบ้าน
conn = st.connection("gsheets", type=GSheetsConnection)

# ฟังก์ชันดึงข้อมูลจาก Google Sheets
def load_data():
    try:
        # ดึงข้อมูลจากแผ่นงานหลัก (ถ้ายังไม่มีข้อมูล จะสร้าง DataFrame เปล่าที่มีคอลัมน์พร้อมใช้งาน)
        df = conn.read(ttl="0d") # ttl="0d" คือดึงข้อมูลสดใหม่ทุกครั้ง ไม่ดึงจากแคช
        df = df.dropna(how="all")
        return df
    except Exception:
        # กรณีรันครั้งแรกและชีตยังว่างเปล่า ให้สร้างโครงสร้างคอลัมน์เริ่มต้นไว้ก่อน
        columns = [
            'รหัสระบบ', 'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม',
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก',
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่',
            'เบอร์โทรศัพท์เจ้าของ', 'เบอร์โทรศัพท์ผู้จัดการ'
        ]
        return pd.DataFrame(columns=columns)

# ฟังก์ชันบันทึก DataFrame กลับลง Google Sheets
def save_data(df_to_save):
    conn.update(data=df_to_save)
    st.cache_data.clear()

# โหลดข้อมูลปัจจุบันมาใช้งาน
df_source = load_data()

# รายการตัวเลือกต่าง ๆ สำหรับงานทะเบียนอำเภอเมืองประจวบฯ
SUBDISTRICTS = ["ตำบลเกาะหลัก", "ตำบลอ่าวน้อย", "ตำบลคลองวาฬ", "ตำบลห้วยทราย", "ตำบลบ่อนอก", "เขตเทศบาลเมืองประจวบคีรีขันธ์"]
HOTEL_TYPES = ["ประเภท 1 (เฉพาะห้องพัก)", "ประเภท 2 (ห้องพัก + ห้องอาหาร)", "ประเภท 3 (ห้องพัก + อาหาร + สถานบริการ)", "ประเภท 4", "ประเภท 5 ไม่เป็นโรงแรม"]
FEE_STATUS_OPTIONS = ["จ่ายแล้ว", "ค้างชำระ", "ไม่มีค่าธรรมเนียม"]

# 3. เมนูแยกแท็บใช้งาน
tab1, tab2 = st.tabs(["📋 ดูข้อมูลและออกรายงาน", "➕ เพิ่มทะเบียนโรงแรมใหม่"])

with tab1:
    if not df_source.empty and len(df_source) > 0:
        today = date.today()
        remaining_days = []
        status_labels = []

        # แปลงข้อมูลความปลอดภัยและคำนวณวันหมดอายุ
        for idx, row in df_source.iterrows():
            expiry = row.get('วันหมดอายุ', '')
            if pd.notnull(expiry) and str(expiry).strip() != "":
                try:
                    expiry_str = str(expiry).split()[0]
                    expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                    delta = expiry_dt - today
                    days = delta.days
                    remaining_days.append(days)
                    
                    if days <= 0: status_labels.append("🔴 หมดอายุแล้ว")
                    elif days <= 90: status_labels.append("🟡 ใกล้หมดอายุ (น้อยกว่า 90 วัน)")
                    else: status_labels.append("🟢 ปกติ")
                except Exception:
                    remaining_days.append(None)
                    status_labels.append("⚪ รูปแบบวันที่ผิดพลาด")
            else:
                remaining_days.append(None)
                status_labels.append("⚪ ไม่มีข้อมูลใบอนุญาต")

        df_source['วันคงเหลือ (วัน)'] = remaining_days
        df_source['สถานะใบอนุญาต'] = status_labels

        # ส่วนแสดงผลเมทริกซ์สรุปตัวเลขของอำเภอ
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("โรงแรมทั้งหมดในอำเภอ", len(df_source))
        col2.metric("🟢 Status ปกติ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟢 ปกติ"]))
        col3.metric("🟡 ใกล้หมดอายุ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟡 ใกล้หมดอายุ (น้อยกว่า 90 วัน)"]))
        col4.metric("🔴 หมดอายุแล้ว", len(df_source[df_source['สถานะใบอนุญาต'] == "🔴 หมดอายุแล้ว"]))
        
        st.markdown("---")
        st.markdown("### 🔍 ค้นหาข้อมูลโรงแรม")
        search_query = st.text_input("พิมพ์ชื่อโรงแรม, เลขใบอนุญาต, ชื่อผู้จัดการ หรือชื่อตำบล เพื่อค้นหา...")
        
        df_filtered = df_source.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['ชื่อโรงแรม'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['เลขที่ใบอนุญาต (ร.บ.2)'].astype(str).str.contains(search_query, na=False) | 
                df_filtered['ชื่อผู้ประกอบการ'].astype(str).str.contains(search_query, na=False) |
                df_filtered['ชื่อผู้จัดการโรงแรม (หน้างาน)'].astype(str).str.contains(search_query, na=False) |
                df_filtered['ที่อยู่'].astype(str).str.contains(search_query, na=False)
            ]

        # รวมเบอร์ติดต่อหน้างาน
        contact_phones = []
        for idx, row in df_filtered.iterrows():
            m_tel = row.get('เบอร์โทรศัพท์ผู้จัดการ', '')
            o_tel = row.get('เบอร์โทรศัพท์เจ้าของ', '')
            m_name = row.get('ชื่อผู้จัดการโรงแรม (หน้างาน)', '')
            if pd.isnull(m_name) or str(m_name).strip() == "" or pd.isnull(m_tel) or str(m_tel).strip() == "":
                contact_phones.append(o_tel if (pd.notnull(o_tel) and str(o_tel).strip() != "") else "-")
            else:
                contact_phones.append(m_tel)
        df_filtered['เบอร์โทรติดต่อหน้างาน'] = contact_phones

        display_cols = [
            'เลขที่ใบอนุญาต (ร.บ.2)', 'ชื่อโรงแรม', 'ประเภทโรงแรม', 
            'ชื่อผู้ประกอบการ', 'ชื่อผู้จัดการโรงแรม (หน้างาน)', 'จำนวนห้องพัก', 
            'วันออกใบอนุญาต', 'วันหมดอายุ', 'วันคงเหลือ (วัน)', 
            'สถานะใบอนุญาต', 'สถานะค่าธรรมเนียมรายปี', 'ที่อยู่', 'เบอร์โทรติดต่อหน้างาน'
        ]
        
        st.markdown("### 📋 ตารางข้อมูลสถานะล่าสุด (จาก Google Sheets)")
        st.dataframe(df_filtered[display_cols], use_container_width=True)
        
        st.markdown("---")
        
        # ⚙️ ส่วนแก้ไขและลบข้อมูล
        st.markdown("### ⚙️ จัดการข้อมูลการจัดการระดับโรงแรม (แก้ไข/ลบข้อมูล)")
        hotel_list = {f"[{str(row['รหัสระบบ']).split('.')[0]}] ใบอนุญาต: {row['เลขที่ใบอนุญาต (ร.บ.2)']} - {row['ชื่อโรงแรม']}": row['รหัสระบบ'] for idx, row in df_filtered.iterrows()}
        selected_hotel_str = st.selectbox("เลือกโรงแรมที่ต้องการจัดการข้อมูล:", ["-- กรุณาเลือกโรงแรม --"] + list(hotel_list.keys()))
        
        if selected_hotel_str != "-- กรุณาเลือกโรงแรม --":
            selected_id = hotel_list[selected_hotel_str]
            hotel_row = df_filtered[df_filtered['รหัสระบบ'] == selected_id].iloc[0]
            
            edit_col, delete_col = st.columns([2, 1])
            with edit_col:
                st.info(f"📝 ฟอร์มแก้ไขข้อมูล: {hotel_row['ชื่อโรงแรม']}")
                with st.form(f"edit_form_{selected_id}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_name = st.text_input("ชื่อโรงแรม *", value=str(hotel_row['ชื่อโรงแรม']))
                        try: default_type_idx = HOTEL_TYPES.index(hotel_row['ประเภทโรงแรม'])
                        except: default_type_idx = 0
                        edit_type = st.selectbox("ประเภทโรงแรม *", HOTEL_TYPES, index=default_type_idx)
                        edit_owner = st.text_input("ชื่อผู้ประกอบการ / เจ้าของ *", value=str(hotel_row['ชื่อผู้ประกอบการ']))
                        edit_manager = st.text_input("ชื่อผู้จัดการโรงแรม (หน้างาน)", value=str(hotel_row['ชื่อผู้จัดการโรงแรม (หน้างาน)']) if hotel_row['ชื่อผู้จัดการโรงแรม (หน้างาน)'] and str(hotel_row['ชื่อผู้จัดการโรงแรม (หน้างาน)']) != 'None' else "")
                        edit_rooms = st.number_input("จำนวนห้องพักทั้งหมด *", min_value=1, step=1, value=int(float(hotel_row['จำนวนห้องพัก'])))
                    
                    with ec2:
                        edit_tel = st.text_input("เบอร์โทรศัพท์เจ้าของ", value=str(hotel_row['เบอร์โทรศัพท์เจ้าของ']) if hotel_row['เบอร์โทรศัพท์เจ้าของ'] and str(hotel_row['เบอร์โทรศัพท์เจ้าของ']) != 'None' else "")
                        edit_manager_tel = st.text_input("เบอร์โทรศัพท์ผู้จัดการ (ติดต่อด่วน)", value=str(hotel_row['เบอร์โทรศัพท์ผู้จัดการ']) if hotel_row['เบอร์โทรศัพท์ผู้จัดการ'] and str(hotel_row['เบอร์โทรศัพท์ผู้จัดการ']) != 'None' else "")
                        edit_l_no = st.text_input("เลขที่ใบอนุญาต ร.บ. 2 *", value=str(hotel_row['เลขที่ใบอนุญาต (ร.บ.2)']) if hotel_row['เลขที่ใบอนุญาต (ร.บ.2)'] and str(hotel_row['เลขที่ใบอนุญาต (ร.บ.2)']) != 'None' else "")
                        
                        try: current_issue = datetime.strptime(str(hotel_row['วันออกใบอนุญาต']).split()[0], "%Y-%m-%d").date()
                        except: current_issue = date.today()
                        try: current_expiry = datetime.strptime(str(hotel_row['วันหมดอายุ']).split()[0], "%Y-%m-%d").date()
                        except: current_expiry = date.today()
                            
                        edit_l_issue = st.date_input("วันที่ออกใบอนุญาต", current_issue)
                        edit_l_expiry = st.date_input("วันที่ใบอนุญาตหมดอายุ", current_expiry)
                        try: default_fee_idx = FEE_STATUS_OPTIONS.index(hotel_row['สถานะค่าธรรมเนียมรายปี'])
                        except: default_fee_idx = 0
                        edit_l_fee = st.selectbox("สถานะค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS, index=default_fee_idx)
                    
                    current_full_address = str(hotel_row['ที่อยู่'])
                    detected_sub_idx = 0
                    for sub_idx, sub_name in enumerate(SUBDISTRICTS):
                        if sub_name in current_full_address:
                            detected_sub_idx = sub_idx
                            break
                    edit_subdistrict = st.selectbox("เลือกตำบล/เขตเทศบาล *", SUBDISTRICTS, index=detected_sub_idx, key="edit_sub_select")
                    clean_address_detail = current_full_address.replace(edit_subdistrict, "").strip()
                    edit_address_detail = st.text_input("ที่อยู่เพิ่มเติม (เลขที่, หมู่, ถนน, ซอย) *", value=clean_address_detail)
                    
                    update_btn = st.form_submit_button("🆙 อัปเดตข้อมูลไปยัง Google Sheets")
                    if update_btn:
                        idx_to_update = df_source[df_source['รหัสระบบ'] == selected_id].index[0]
                        df_source.at[idx_to_update, 'ชื่อโรงแรม'] = edit_name
                        df_source.at[idx_to_update, 'ประเภทโรงแรม'] = edit_type
                        df_source.at[idx_to_update, 'ชื่อผู้ประกอบการ'] = edit_owner
                        df_source.at[idx_to_update, 'ชื่อผู้จัดการโรงแรม (หน้างาน)'] = edit_manager
                        df_source.at[idx_to_update, 'จำนวนห้องพัก'] = edit_rooms
                        df_source.at[idx_to_update, 'เบอร์โทรศัพท์เจ้าของ'] = edit_tel
                        df_source.at[idx_to_update, 'เบอร์โทรศัพท์ผู้จัดการ'] = edit_manager_tel
                        df_source.at[idx_to_update, 'เลขที่ใบอนุญาต (ร.บ.2)'] = edit_l_no
                        df_source.at[idx_to_update, 'วันออกใบอนุญาต'] = str(edit_l_issue)
                        df_source.at[idx_to_update, 'วันหมดอายุ'] = str(edit_l_expiry)
                        df_source.at[idx_to_update, 'สถานะค่าธรรมเนียมรายปี'] = edit_l_fee
                        df_source.at[idx_to_update, 'ที่อยู่'] = f"{edit_address_detail} {edit_subdistrict}"
                        
                        save_data(df_source)
                        st.success("🎉 อัปเดตข้อมูลบน Google Sheets เรียบร้อยแล้ว!")
                        st.rerun()
                        
            with delete_col:
                st.warning("⚠️ ลบข้อมูล")
                confirm_delete = st.checkbox("ยืนยันว่าต้องการลบโรงแรมนี้จริง ๆ")
                if st.button("🗑️ ลบออกจาก Google Sheets", type="primary", disabled=not confirm_delete):
                    df_source = df_source[df_source['รหัสระบบ'] != selected_id]
                    save_data(df_source)
                    st.success("🗑️ ลบข้อมูลเรียบร้อยแล้ว!")
                    st.rerun()

        # ปุ่มดาวน์โหลด Excel สรุปผล
        st.markdown("---")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtered[display_cols].to_excel(writer, index=False, sheet_name='รายงานสรุป')
        st.download_button(
            label="📥 ดาวน์โหลดรายงานสรุป (Excel)",
            data=output.getvalue(),
            file_name=f"รายงานสรุปทะเบียนโรงแรม_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("💡 ปัจจุบันไม่มีข้อมูลใน Google Sheets ลองไปเพิ่มข้อมูลที่แท็บด้านบนได้เลยครับ")

with tab2:
    st.markdown("### 📝 ฟอร์มลงทะเบียนโรงแรมและใบอนุญาตตัวใหม่")
    with st.form("hotel_add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            h_name = st.text_input("ชื่อโรงแรม *")
            h_type = st.selectbox("ประเภทโรงแรม *", HOTEL_TYPES)
            h_owner = st.text_input("ชื่อผู้ประกอบการ / เจ้าของ *")
            h_manager = st.text_input("ชื่อผู้จัดการโรงแรม (หน้างาน)")
            h_rooms = st.number_input("จำนวนห้องพักทั้งหมด *", min_value=1, step=1)
        with c2:
            h_tel = st.text_input("เบอร์โทรศัพท์เจ้าของ")
            h_manager_tel = st.text_input("เบอร์โทรศัพท์ผู้จัดการ (ติดต่อด่วน)")
            l_no = st.text_input("เลขที่ใบอนุญาต ร.บ. 2 *")
            l_issue = st.date_input("วันที่ออกใบอนุญาต", date.today())
            l_expiry = st.date_input("วันที่ใบอนุญาตหมดอายุ", date.today())
            l_fee = st.selectbox("สถานะค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS)
            
        st.markdown("---")
        st.markdown("**📍 ข้อมูลที่อยู่ตำแหน่งโรงแรม**")
        addr_col1, addr_col2 = st.columns([1, 2])
        with addr_col1: h_subdistrict = st.selectbox("เลือกตำบล/เขตเทศบาล *", SUBDISTRICTS)
        with addr_col2: h_address_detail = st.text_input("ที่อยู่เพิ่มเติม (ระบุเลขที่บ้าน, หมู่ที่, ถนน, ซอย) *")
            
        submit_btn = st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets")
        if submit_btn:
            if not h_name or not h_owner or not l_no or not h_address_detail:
                st.error("❌ กรุณากรอกข้อมูลในช่องที่มีเครื่องหมาย * ให้ครบถ้วน")
            else:
                full_address = f"{h_address_detail} {h_subdistrict}"
                # สร้าง ID ระบบโดยเช็คจากลำดับแถว
                next_id = int(df_source['รหัสระบบ'].max() + 1) if not df_source.empty and df_source['รหัสระบบ'].notnull().any() else 1
                
                new_row = {
                    'รหัสระบบ': next_id, 'เลขที่ใบอนุญาต (ร.บ.2)': l_no, 'ชื่อโรงแรม': h_name,
                    'ประเภทโรงแรม': h_type, 'ชื่อผู้ประกอบการ': h_owner, 'ชื่อผู้จัดการโรงแรม (หน้างาน)': h_manager,
                    'จำนวนห้องพัก': h_rooms, 'วันออกใบอนุญาต': str(l_issue), 'วันหมดอายุ': str(l_expiry),
                    'สถานะค่าธรรมเนียมรายปี': l_fee, 'ที่อยู่': full_address, 'เบอร์โทรศัพท์เจ้าของ': h_tel,
                    'เบอร์โทรศัพท์ผู้จัดการ': h_manager_tel
                }
                
                df_source = pd.concat([df_source, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df_source)
                st.success(f"🎉 บันทึกข้อมูลโรงแรม '{h_name}' ลง Google Sheets เรียบร้อยแล้ว!")
                st.rerun()
