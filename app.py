import streamlit as st
from supabase import create_client
import pandas as pd

# 1. เชื่อมต่อกับ Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("ระบบจัดการข้อมูลโรงแรม")

# 2. ฟังก์ชันดึงข้อมูลจากตาราง hotels
def get_hotels():
    response = supabase.table("hotels").select("*").execute()
    return pd.DataFrame(response.data)

# 3. ตัวอย่างการแสดงผลและเพิ่มข้อมูล
tab1, tab2 = st.tabs(["ดูข้อมูลโรงแรม", "เพิ่มข้อมูลโรงแรม"])

with tab1:
    st.subheader("รายชื่อโรงแรม")
    df = get_hotels()
    if not df.empty:
        st.dataframe(df)
    else:
        st.write("ยังไม่มีข้อมูลในฐานข้อมูลครับ")

with tab2:
    st.subheader("เพิ่มโรงแรมใหม่")
    with st.form("hotel_form"):
        name = st.text_input("ชื่อโรงแรม")
        h_type = st.text_input("ประเภทโรงแรม")
        submit = st.form_submit_button("บันทึกข้อมูล")
        
        if submit:
            # ส่งข้อมูลไป Supabase
            data = {"hotel_name": name, "hotel_type": h_type}
            supabase.table("hotels").insert(data).execute()
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
            st.rerun() # สั่งรีเฟรชหน้าจอเพื่อดึงข้อมูลใหม่
