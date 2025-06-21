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

# Khởi tạo state nếu chưa có
if "question" not in st.session_state:
    st.session_state["question"] = ""
if "answer" not in st.session_state:
    st.session_state["answer"] = ""
if "status_msg" not in st.session_state:
    st.session_state["status_msg"] = ""

# Define callback function for retrieve
def retrieve_data():
    q = st.session_state["question"].strip()
    a = st.session_state["answer"].strip()
    
    if q:
        record = faq_collection.find_one({"Question": q})
        if record:
            st.session_state["answer"] = record.get("Answer", "")
            st.session_state["status_msg"] = "✅ Đã tìm thấy câu hỏi và điền sẵn câu trả lời."
        else:
            st.session_state["status_msg"] = "⚠️ Không tìm thấy câu hỏi trong cơ sở dữ liệu."
    elif a:
        record = faq_collection.find_one({"Answer": a})
        if record:
            st.session_state["question"] = record.get("Question", "")
            st.session_state["status_msg"] = "✅ Đã tìm thấy câu trả lời và điền sẵn câu hỏi."
        else:
            st.session_state["status_msg"] = "⚠️ Không tìm thấy câu trả lời trong cơ sở dữ liệu."
    else:
        st.session_state["status_msg"] = "⚠️ Vui lòng nhập ít nhất một trong hai trường."

# Giao diện nhập
st.text_input("❓ Câu hỏi (Question)", key="question")
st.text_area("💬 Câu trả lời (Answer)", key="answer", height=150)

# Nút Retrieve
st.button("🔍 Retrieve", on_click=retrieve_data)

# Hiển thị trạng thái
if st.session_state["status_msg"]:
    st.info(st.session_state["status_msg"])

# Nút cập nhật
if st.button("💾 Update"):
    q = st.session_state["question"].strip()
    a = st.session_state["answer"].strip()
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
