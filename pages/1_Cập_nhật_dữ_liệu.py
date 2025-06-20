import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
faq_collection = db["faqtuyensinh"]

st.set_page_config(page_title="Cập nhật FAQ từ Excel", page_icon="📄")
st.title("📄 Cập nhật câu trả lời trong FAQ từ Excel")

# Upload Excel file
uploaded_file = st.file_uploader("Tải lên file Excel (phải có cột 'Question' và 'Answer')", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        required_columns = {"Question", "Answer"}

        if not required_columns.issubset(df.columns):
            st.error("❌ File phải chứa đúng hai cột: 'Question' và 'Answer'.")
        else:
            st.subheader("📌 Xem trước dữ liệu")
            st.dataframe(df.head(10))

            if st.button("🔄 Bắt đầu cập nhật"):
                update_count = 0
                current_time = datetime.utcnow()

                for _, row in df.iterrows():
                    result = faq_collection.update_one(
                        {"Question": row["Question"]},
                        {
                            "$set": {
                                "Answer": row["Answer"],
                                "CreatedAt": current_time,
                                "LastedUpdate": current_time
                            }
                        }
                    )
                    if result.modified_count > 0:
                        update_count += 1

                st.success(f"✅ Cập nhật thành công {update_count} bản ghi trong cơ sở dữ liệu.")
    except Exception as e:
        st.error(f"Lỗi khi xử lý file: {e}")
