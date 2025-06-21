import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
faq_collection = db["faqtuyensinh"]

st.set_page_config(page_title="📝 Cập nhật thủ công FAQ", page_icon="📝")
st.title("📝 Cập nhật thủ công một câu hỏi trong FAQ")

# Nhập liệu
question_input = st.text_input("❓ Câu hỏi (Question)")
answer_input = st.text_area("💬 Câu trả lời (Answer)", height=150)

# Nút truy xuất
if st.button("🔍 Retrieve"):
    if question_input:
        record = faq_collection.find_one({"Question": question_input})
        if record:
            answer_input = record.get("Answer", "")
            st.success("✅ Tìm thấy câu hỏi. Bạn có thể chỉnh sửa câu trả lời.")
            st.experimental_rerun()
        else:
            st.warning("⚠️ Không tìm thấy câu hỏi trong cơ sở dữ liệu.")
    elif answer_input:
        record = faq_collection.find_one({"Answer": answer_input})
        if record:
            question_input = record.get("Question", "")
            st.success("✅ Tìm thấy câu trả lời. Bạn có thể chỉnh sửa câu hỏi.")
            st.experimental_rerun()
    else:
        st.warning("⚠️ Vui lòng nhập ít nhất một trong hai trường để tìm kiếm.")

# Nút cập nhật
if st.button("💾 Update"):
    if question_input and answer_input:
        current_time = datetime.utcnow()
        result = faq_collection.update_one(
            {"Question": question_input},
            {
                "$set": {
                    "Answer": answer_input,
                    "LastedUpdate": current_time
                },
                "$setOnInsert": {
                    "CreatedAt": current_time
                }
            },
            upsert=True
        )
        if result.modified_count > 0 or result.upserted_id:
            st.success("✅ Dữ liệu đã được cập nhật thành công.")
        else:
            st.info("ℹ️ Không có thay đổi nào được thực hiện.")
    else:
        st.error("❌ Cần nhập đầy đủ cả Câu hỏi và Câu trả lời để cập nhật.")
