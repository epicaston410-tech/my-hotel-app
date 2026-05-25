import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="ระบบทะเบียนโรงแรม", layout="wide")

st.title("🏨 ระบบงานทะเบียนโรงแรม")

# เชื่อมต่อ Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="hotels")
    st.success("เชื่อมต่อ Google Sheets สำเร็จ!")
    st.dataframe(df, use_container_width=True)
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
    st.info("กรุณาตรวจสอบว่ามีไฟล์ชื่อ 'hotels' ใน Google Sheets ของคุณแล้ว")
