import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
faq_collection = db["faqtuyensinh"]

st.set_page_config(page_title="📝 Cập nhật FAQ thủ công", page_icon="📝")
st.title("📝 Cập nhật câu hỏi - FAQ (1 bản ghi mỗi lần)")

# Khởi tạo session state
if "question" not in st.session_state:
    st.session_state.question = ""
if "answer" not in st.session_state:
    st.session_state.answer = ""

# Nhập liệu
st.text_input("❓ Câu hỏi (Question)", key="question")
st.text_area("💬 Câu trả lời (Answer)", key="answer", height=150)

# Nút truy xuất
if st.button("🔍 Retrieve"):
    if st.session_state.question:
        record = faq_collection.find_one({"Question": st.session_state.question})
        if record:
            st.session_state.answer = record.get("Answer", "")
            st.success("✅ Đã tìm thấy câu hỏi và điền sẵn câu trả lời.")
        else:
            st.warning("⚠️ Không tìm thấy câu hỏi trong cơ sở dữ liệu.")
    elif st.session_state.answer:
        record = faq_collection.find_one({"Answer": st.session_state.answer})
        if record:
            st.session_state.question = record.get("Question", "")
            st.success("✅ Đã tìm thấy câu trả lời và điền sẵn câu hỏi.")
        else:
            st.warning("⚠️ Không tìm thấy câu trả lời trong cơ sở dữ liệu.")
    else:
        st.warning("⚠️ Vui lòng nhập ít nhất một trong hai trường.")

# Nút cập nhật
if st.button("💾 Update"):
    q = st.session_state.question.strip()
    a = st.session_state.answer.strip()
    if q and a:
        current_time = datetime.utcnow()
        result = faq_collection.update_one(
            {"Question": q},
            {
                "$set": {
                    "Answer": a,
                    "LastedUpdate": current_time
                },
                "$setOnInsert": {
                    "CreatedAt": current_time
                }
            },
            upsert=True
        )
        if result.modified_count > 0 or result.upserted_id:
            st.success("✅ Cập nhật thành công.")
        else:
            st.info("ℹ️ Không có thay đổi nào được thực hiện.")
    else:
        st.error("❌ Vui lòng nhập đầy đủ cả Câu hỏi và Câu trả lời để cập nhật.")
