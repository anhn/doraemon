import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
chatlog_collection = db["chatlog"]

# Giao diện
st.set_page_config(page_title="📜 Lịch sử Hội thoại", page_icon="💬")
st.title("💬 Tra cứu các hội thoại từ chatlog")

# Chọn ngày
selected_date = st.date_input("📅 Chọn ngày muốn xem hội thoại", datetime.today())

if st.button("🔍 Retrieve"):
    try:
        # Xác định thời gian bắt đầu và kết thúc trong ngày
        start_time = datetime.combine(selected_date, datetime.min.time())
        end_time = datetime.combine(selected_date, datetime.max.time())

        # Truy vấn các bản ghi có createdAt trong ngày và chỉ lấy các trường cần thiết
        cursor = chatlog_collection.find(
            {"createdAt": {"$gte": start_time, "$lte": end_time}},
            {
                "user_ip": 1,
                "user_message": 1,
                "bot_response": 1,
                "is_good": 1,
                "createdAt": 1,
                "_id": 0
            }
        ).sort("createdAt", -1)

        # Chuyển đổi kết quả thành DataFrame
        data = list(cursor)
        if not data:
            st.info("📭 Không có hội thoại nào trong ngày được chọn.")
        else:
            df = pd.DataFrame(data)
            df["createdAt"] = pd.to_datetime(df["createdAt"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            st.success(f"✅ Tìm thấy {len(df)} hội thoại.")
            st.dataframe(df)

    except Exception as e:
        st.error(f"❌ Lỗi khi truy vấn dữ liệu: {e}")
