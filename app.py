import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบทะเบียนโรงแรม", layout="wide")

st.title("🏨 ระบบงานทะเบียนโรงแรม")
st.markdown("กรมการปกครอง ที่ว่าการอำเภอเมืองประจวบคีรีขันธ์")
st.markdown("---")

# 2. เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. เมนูหลัก
tab1, tab2 = st.tabs(["📋 ดูข้อมูล", "➕ เพิ่มข้อมูล"])

with tab1:
    st.subheader("ข้อมูลโรงแรมทั้งหมด")
    try:
        df = conn.read(worksheet="hotels")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"ยังดึงข้อมูลไม่ได้: {e}")

with tab2:
    st.subheader("เพิ่มข้อมูลโรงแรมใหม่")
    with st.form("add_form", clear_on_submit=True):
        h_name = st.text_input("ชื่อโรงแรม")
        submit = st.form_submit_button("บันทึก")
        if submit:
            st.warning("ฟังก์ชันบันทึกข้อมูลกำลังพัฒนาต่อหลังจากหน้านี้รันผ่านครับ")
