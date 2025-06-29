import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import re

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
faq_collection = db["faqtuyensinh"]
score_collection = db["diemchuan"]

st.set_page_config(page_title="Cập nhật FAQ từ Excel", page_icon="📄")

st.title("📄 Cập nhật lại bảng điểm chuẩn trong Mongo Db")

# Hàm trích xuất thông tin từ câu hỏi và trả lời
def extract_score_data(faq_data):
    extracted = []
    for item in faq_data:
        q = item["Question"]
        a = item["Answer"]
        try:
            year_match = re.search(r"năm (\d{4})", q)
            score_type_match = re.search(r"Điểm chuẩn\s+(THPT|học bạ)", q, re.IGNORECASE)
            field_match = re.search(r"ngành (.*?) năm", q, re.IGNORECASE)

            if year_match and score_type_match and field_match:
                year = int(year_match.group(1))
                score_type = score_type_match.group(1).strip().lower()
                field = field_match.group(1).strip()
                score = float(a.strip())

                extracted.append({
                    "Question": q,
                    "Answer": a,
                    "ScoreType": score_type,
                    "Field": field,
                    "Year": year,
                    "Score": score
                })
        except:
            continue
    return extracted

if st.button("📥 Cập nhật dữ liệu điểm chuẩn"):
    with st.spinner("Đang xử lý..."):
        faq_data = list(faq_collection.find({}, {"_id": 0, "Question": 1, "Answer": 1}))
        extracted_data = extract_score_data(faq_data)

        # Xóa collection cũ và ghi dữ liệu mới
        score_collection.delete_many({})
        if extracted_data:
            score_collection.insert_many(extracted_data)
            df = pd.DataFrame(extracted_data)
            st.success(f"✅ Đã cập nhật {len(extracted_data)} bản ghi vào collection `diemchuan`.")
            st.dataframe(df)
        else:
            st.warning("⚠️ Không có dữ liệu phù hợp được trích xuất.")

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
