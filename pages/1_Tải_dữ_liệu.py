import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
faq_collection = db["faqtuyensinh"]

st.set_page_config(page_title="Quản lý Câu hỏi FAQ", page_icon="📄")

st.title("📄 Tải lên dữ liệu Câu hỏi - FAQ")

# Chọn chế độ thao tác dữ liệu
#mode = st.radio("Chọn chế độ lưu dữ liệu:", ("Thêm vào dữ liệu hiện có", "Xóa toàn bộ dữ liệu cũ và thêm mới"))
mode = st.radio("Chọn chế độ lưu dữ liệu:", ("Thêm vào dữ liệu hiện có"))

# Tải lên tệp Excel
uploaded_file = st.file_uploader("Tải lên file Excel (xlsx) chứa cột Question và Answer", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        required_columns = {"Question", "Answer"}

        if not required_columns.issubset(df.columns):
            st.error("❌ File phải chứa 2 cột bắt buộc: 'Question' và 'Answer'.")
        else:
            current_time = datetime.utcnow()
            df["CreatedAt"] = current_time
            df["LastedUpdate"] = current_time

            st.subheader("📌 Xem trước dữ liệu")
            st.dataframe(df.head(10))

            if st.button("💾 Lưu vào cơ sở dữ liệu"):
                data = df.to_dict(orient="records")
                if mode == "Xóa toàn bộ dữ liệu cũ và thêm mới":
                    faq_collection.delete_many({})
                    faq_collection.insert_many(data)
                    st.success("✅ Dữ liệu đã được cập nhật (đã xóa dữ liệu cũ).")
                else:
                    faq_collection.insert_many(data)
                    st.success("✅ Dữ liệu đã được thêm vào.")
    except Exception as e:
        st.error(f"Lỗi khi đọc file: {e}")
