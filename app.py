import streamlit as st
from supabase import create_client
from PIL import Image
import pandas as pd
from datetime import date, datetime
import io
import os
import base64

# 1. ตั้งค่าหน้าเว็บให้กว้างและสะอาด สไตล์งานราชการ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม - อำเภอ", layout="wide")

# เชื่อมต่อกับ Supabase ผ่าน Secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- ฟังก์ชันดึงรูปภาพจากโฟลเดอร์ static และแปลงเป็น Base64 ---
def get_image_base64(image_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "static", image_name)
    
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

# ดึงรูปจากโฟลเดอร์ static 
img_base64 = get_image_base64("dopa.png")

# กำหนดแหล่งที่มารูปภาพ
if img_base64:
    img_src = f"data:image/png;base64,{img_base64}"
else:
    img_src = "https://raw.githubusercontent.com/streamlit/proactive-connectors/main/branding/logo.png"

# --- ส่วนหัวของระบบ (แก้ใหม่: เอาวงกลมออก เพื่อให้ตราดูใหญ่ขึ้น) ---
st.html(f"""
    <div style='display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding: 10px;'>
        <img src='{img_src}' style='width: 120px; height: auto; object-fit: contain;' onerror="this.src='https://img.icons8.com/color/96/000000/goverment.png';">
        <div style='text-align: left;'>
            <h1 style='font-size: 38px; font-weight: bold; margin: 0 0 5px 0; color: #003366;'>
                 &nbsp;ระบบงานทะเบียนโรงแรม
            </h1>
            <h2 style='font-size: 24px; font-weight: normal; color: #555555; margin: 0;'>
                กรมการปกครอง ที่ว่าการอำเภอเมืองประจวบคีรีขันธ์
            </h2>
        </div>
    </div>
""")

st.markdown("---")

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

# 2. ฟังก์ชันโหลดข้อมูลย้ายมาดึงจาก Supabase (รองรับการ Join ตารางอัตโนมัติ)
def load_data():
    try:
        response = supabase.table("hotels").select("*, licenses(*)").execute()
        data = []
        for h in response.data:
            # ดึงข้อมูลใบอนุญาตจากตารางลูก (Relation Link)
            license_list = h.get('licenses', [])
            lic = license_list[0] if license_list else {}
            
            row = {
                'รหัสระบบ': h.get('id'),
                'เลขที่ใบอนุญาต': lic.get('license_no', '-'),
                'ชื่อโรงแรม': h.get('hotel_name', ''),
                'ประเภทโรงแรม': h.get('hotel_type', ''),
                'ชื่อผู้ประกอบการ': h.get('owner_name', ''),
                'ชื่อผู้จัดการโรงแรม (หน้างาน)': h.get('manager_name', ''),
                'จำนวนห้องพัก': h.get('total_rooms', 0),
                'วันออกใบอนุญาต': lic.get('issue_date', ''),
                'วันหมดอายุ': lic.get('expiry_date', ''),
                'สถานะค่าธรรมเนียมรายปี': lic.get('fee_status', 'ไม่มีค่าธรรมเนียม'),
                'ที่อยู่': h.get('address', ''),
                'เบอร์โทรศัพท์เจ้าของ': h.get('tel', ''),
                'เบอร์โทรศัพท์ผู้จัดการ': h.get('manager_tel', '')
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values(by='เลขที่ใบอนุญาต', ascending=True).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถเชื่อมต่อฐานข้อมูล Supabase ได้: {e}")
        return pd.DataFrame()

# ฟังก์ชันลบข้อมูลออกจากระบบ (Cascading Delete ทำงานอัตโนมัติฝั่งระบบฐานข้อมูล)
def delete_hotel(hotel_id):
    try:
        supabase.table("hotels").delete().eq("id", hotel_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {e}")
        return False

# ฟังก์ชันแปลงไฟล์ออกมาเป็น Excel สรุปรายงานข้อมูล
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

# 3. เมนูแยกแท็บใช้งานหลัก
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
        col2.metric("🟢 Status ปกติ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟢 ปกติ"]))
        col3.metric("🟡 ใกล้หมดอายุ", len(df_source[df_source['สถานะใบอนุญาต'] == "🟡 ใกล้หมดอายุ (น้อยกว่า 90 วัน)"]))
        col4.metric("🔴 หมดอายุแล้ว", len(df_source[df_source['สถานะใบอนุญาต'] == "🔴 หมดอายุแล้ว"]))
        
        st.markdown("---")

        st.markdown("### 🔍 ค้นหาข้อมูลโรงแรม")
        search_query = st.text_input("พิมพ์ชื่อโรงแรม, เลขใบอนุญาต, ชื่อผู้จัดการ หรือชื่อตำบล เพื่อค้นหา...")
        
        df_filtered = df_source.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['ชื่อโรงแรม'].str.contains(search_query, na=False) | 
                df_filtered['เลขที่ใบอนุญาต'].str.contains(search_query, na=False) | 
                df_filtered['ชื่อผู้ประกอบการ'].str.contains(search_query, na=False) |
                df_filtered['ชื่อผู้จัดการโรงแรม (หน้างาน)'].str.contains(search_query, na=False) |
                df_filtered['ที่อยู่'].str.contains(search_query, na=False)
            ]

        st.markdown("### 📋 ตารางข้อมูลสถานะล่าสุด")
        
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

        display_cols = [
            'เลขที่ใบอนุญาต', 'ชื่อโรงแรม', 'ประเภทโรงแรม', 
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
            
            # --- ส่วนที่เพิ่มเข้ามาใหม่เพื่อตัดคำให้สั้นลงเฉพาะตอนโชว์ตาราง ---
            df_display = df_page[display_cols].copy()
            df_display['ประเภทโรงแรม'] = df_display['ประเภทโรงแรม'].apply(
                lambda x: str(x).split(' (')[0].replace(' ไม่เป็นโรงแรม', '') if pd.notnull(x) else x
            )
            
            st.dataframe(df_display, use_container_width=True)
            
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
        hotel_list = {f"[{row['รหัสระบบ']}] ใบอนุญาต: {row['เลขที่ใบอนุญาต']} - {row['ชื่อโรงแรม']}": row['รหัสระบบ'] for idx, row in df_filtered.iterrows()}
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
                        edit_rooms = st.number_input("จำนวนห้องพักทั้งหมด *", min_value=1, step=1, value=int(hotel_row['จำนวนห้องพัก']))
                    
                    with ec2:
                        edit_tel = st.text_input("เบอร์โทรศัพท์เจ้าของ", value=str(hotel_row['เบอร์โทรศัพท์เจ้าของ']) if hotel_row['เบอร์โทรศัพท์เจ้าของ'] and str(hotel_row['เบอร์โทรศัพท์เจ้าของ']) != 'None' else "")
                        edit_manager_tel = st.text_input("เบอร์โทรศัพท์ผู้จัดการ (ติดต่อด่วน)", value=str(hotel_row['เบอร์โทรศัพท์ผู้จัดการ']) if hotel_row['เบอร์โทรศัพท์ผู้จัดการ'] and str(hotel_row['เบอร์โทรศัพท์ผู้จัดการ']) != 'None' else "")
                        edit_l_no = st.text_input("เลขที่ใบอนุญาต *", value=str(hotel_row['เลขที่ใบอนุญาต']) if hotel_row['เลขที่ใบอนุญาต'] and str(hotel_row['เลขที่ใบอนุญาต']) != 'None' else "")
                        
                        try: current_issue = datetime.strptime(str(hotel_row['วันออกใบอนุญาต']), "%Y-%m-%d").date()
                        except: current_issue = date.today()
                        try: current_expiry = datetime.strptime(str(hotel_row['วันหมดอายุ']), "%Y-%m-%d").date()
                        except: current_expiry = date.today()
                            
                        edit_l_issue = st.date_input("วันที่ออกใบอนุญาต", current_issue)
                        edit_l_expiry = st.date_input("วันที่ใบอนุญาตหมดอายุ (มีอายุ 5 ปี)", current_expiry)
                        
                        try: default_fee_idx = FEE_STATUS_OPTIONS.index(hotel_row['สถานะค่าธรรมเนียมรายปี'])
                        except: default_fee_idx = 0
                        edit_l_fee = st.selectbox("สถานะค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS, index=default_fee_idx)
                    
                    st.markdown("**📍 แก้ไขข้อมูลที่อยู่ตำแหน่งโรงแรม**")
                    current_full_address = str(hotel_row['ที่อยู่']) if hotel_row['ที่อยู่'] else ""
                    
                    detected_sub_idx = 0
                    for sub_idx, sub_name in enumerate(SUBDISTRICTS):
                        if sub_name in current_full_address:
                            detected_sub_idx = sub_idx
                            break
                    
                    edit_subdistrict = st.selectbox("เลือกตำบล/เขตเทศบาล *", SUBDISTRICTS, index=detected_sub_idx, key="edit_sub_select")
                    clean_address_detail = current_full_address.replace(edit_subdistrict, "").strip()
                    edit_address_detail = st.text_input("ที่อยู่เพิ่มเติม (เลขที่, หมู่, ถนน, ซอย) *", value=clean_address_detail)
                    
                    update_btn = st.form_submit_button("🆙 อัปเดตข้อมูลที่แก้ไข")
                    
                    if update_btn:
                        if not edit_name or not edit_owner or not edit_l_no or not edit_address_detail:
                            st.error("❌ กรุณากรอกข้อมูลและรายละเอียดที่อยู่ให้ครบถ้วน")
                        else:
                            final_address = f"{edit_address_detail} {edit_subdistrict}"
                            
                            try:
                                # อัปเดตข้อมูลลง Supabase ตารางโรงแรมหลัก
                                supabase.table("hotels").update({
                                    "hotel_name": edit_name,
                                    "hotel_type": edit_type,
                                    "owner_name": edit_owner,
                                    "manager_name": edit_manager,
                                    "manager_tel": edit_manager_tel,
                                    "total_rooms": int(edit_rooms),
                                    "tel": edit_tel,
                                    "address": final_address
                                }).eq("id", int(selected_id)).execute()
                                
                                # อัปเดตข้อมูลใบอนุญาตในตารางลูกที่สัมพันธ์กัน
                                supabase.table("licenses").update({
                                    "license_no": edit_l_no,
                                    "issue_date": str(edit_l_issue),
                                    "expiry_date": str(edit_l_expiry),
                                    "fee_status": edit_l_fee
                                }).eq("hotel_id", int(selected_id)).execute()
                                
                                st.success(f"🎉 อัปเดตข้อมูลระบบของ '{edit_name}' เรียบร้อยแล้ว!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกการแก้ไข: {e}")
                                
            with delete_col:
                st.warning("⚠️ โซนอันตราย: ลบข้อมูล")
                st.write(f"หากโรงแรม **{hotel_row['ชื่อโรงแรม']}** ปิดตัวลงอย่างถาวร พี่สามารถกดปุ่มด้านล่างเพื่อลบออกจากฐานข้อมูลได้ทันที")
                
                confirm_delete = st.checkbox("ยืนยันว่าต้องการลบโรงแรมนี้จริง ๆ")
                if st.button("🗑️ ลบข้อมูลโรงแรมนี้ออกจากระบบ", type="primary", disabled=not confirm_delete):
                    if delete_hotel(selected_id):
                        st.success("🗑️ ลบข้อมูลโรงแรมออกจากฐานข้อมูลเรียบร้อยแล้ว!")
                        st.rerun()
        
        st.markdown("---")
        excel_file = to_excel(df_filtered[display_cols])
        st.download_button(
            label="📥 ปริ้นสรุปข้อมูล: ดาวน์โหลดรายงาน (Excel)",
            data=excel_file,
            file_name=f"รายงานสรุปทะเบียนโรงแรม_{today}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("💡 ปัจจุบันยังไม่มีข้อมูลโรงแรมในระบบฐานข้อมูล ลองไปเพิ่มข้อมูลที่แท็บด้านบนได้เลยครับ")

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
            l_no = st.text_input("เลขที่ใบอนุญาต *")
            l_issue = st.date_input("วันที่ออกใบอนุญาต", date.today())
            l_expiry = st.date_input("วันที่ใบอนุญาตหมดอายุ (มีอายุ 5 ปี)", date.today())
            l_fee = st.selectbox("สถานะค่าธรรมเนียมรายปี", FEE_STATUS_OPTIONS)
            
        st.markdown("---")
        st.markdown("**📍 ข้อมูลที่อยู่ตำแหน่งโรงแรม**")
        addr_col1, addr_col2 = st.columns([1, 2])
        with addr_col1:
            h_subdistrict = st.selectbox("เลือกตำบล/เขตเทศบาล *", SUBDISTRICTS)
        with addr_col2:
            h_address_detail = st.text_input("ที่อยู่เพิ่มเติม (ระบุเลขที่บ้าน, หมู่ที่, ถนน, ซอย) *", placeholder="เช่น 123/4 หมู่ 2 ถนนสละชีพ")
            
        submit_btn = st.form_submit_button("💾 บันทึกข้อมูลลงเครื่อง")
        
        if submit_btn:
            if not h_name or not h_owner or not l_no or not h_address_detail:
                st.error("❌ กรุณากรอกข้อมูลในช่องที่มีเครื่องหมาย * รวมถึงรายละเอียดที่อยู่ให้ครบถ้วน")
            else:
                full_address = f"{h_address_detail} {h_subdistrict}"
                
                try:
                    # 1. ยิงข้อมูลเก็บเข้าตาราง hotels ของ Supabase เป็นอันดับแรก
                    hotel_data = {
                        "hotel_name": h_name,
                        "hotel_type": h_type,
                        "owner_name": h_owner,
                        "manager_name": h_manager,
                        "manager_tel": h_manager_tel,
                        "total_rooms": int(h_rooms),
                        "tel": h_tel,
                        "address": full_address
                    }
                    hotel_res = supabase.table("hotels").insert(hotel_data).execute()
                    
                    # 2. นำไอดีหลักของโรงแรมที่เพิ่งถูก Gen ใหม่จากระบบ ผูกเข้ากับใบอนุญาตของตารางลูก
                    if hotel_res.data:
                        last_id = hotel_res.data[0]['id']
                        
                        license_data = {
                            "hotel_id": last_id,
                            "license_no": l_no,
                            "issue_date": str(l_issue),
                            "expiry_date": str(l_expiry),
                            "fee_status": l_fee
                        }
                        supabase.table("licenses").insert(license_data).execute()
                        
                    st.success(f"🎉 บันทึกข้อมูลโรงแรม '{h_name}' ลงทะเบียนเรียบร้อยแล้ว!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกข้อมูลเข้าสู่ระบบระบบคลาวด์: {e}")
