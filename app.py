import streamlit as st
from supabase import create_client
import pandas as pd

# เชื่อมต่อ Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("ระบบจัดการข้อมูลโรงแรม")

tab1, tab2 = st.tabs(["ดูข้อมูลโรงแรม", "เพิ่มข้อมูลโรงแรม"])

with tab1:
    st.subheader("รายชื่อโรงแรมทั้งหมด")
    response = supabase.table("hotels").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        st.dataframe(df)
    else:
        st.write("ยังไม่มีข้อมูลในระบบ")

with tab2:
    st.subheader("กรอกข้อมูลโรงแรมใหม่")
    with st.form("hotel_form"):
        # ช่องกรอกข้อมูลให้ตรงกับตารางใน Supabase
        col1, col2 = st.columns(2)
        with col1:
            hotel_name = st.text_input("ชื่อโรงแรม")
            hotel_type = st.text_input("ประเภทโรงแรม")
            owner_name = st.text_input("ชื่อเจ้าของ")
        with col2:
            manager_name = st.text_input("ชื่อผู้จัดการ")
            manager_tel = st.text_input("เบอร์ผู้จัดการ")
            total_rooms = st.number_input("จำนวนห้องพัก", min_value=0, step=1)
        
        tel = st.text_input("เบอร์โทรศัพท์โรงแรม")
        address = st.text_area("ที่อยู่โรงแรม")
        
        submit = st.form_submit_button("บันทึกข้อมูลโรงแรม")
        
        if submit:
            data = {
                "hotel_name": hotel_name,
                "hotel_type": hotel_type,
                "owner_name": owner_name,
                "manager_name": manager_name,
                "manager_tel": manager_tel,
                "total_rooms": total_rooms,
                "tel": tel,
                "address": address
            }
            supabase.table("hotels").insert(data).execute()
            st.success("บันทึกข้อมูลสำเร็จ!")
            st.rerun()
