import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# Kết nối MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["utt_detai25"]
chatlog_collection = db["chatlog"]

# Giao diện trang
st.set_page_config(page_title="📜 Lịch sử Hội thoại", page_icon="💬")
st.title("💬 Lịch sử các cuộc hội thoại (chatlog)")

# Chọn ngày
selected_date = st.date_input("📅 Chọn ngày muốn xem hội thoại", datetime.today())

# Nút truy vấn dữ liệu
if st.button("🔍 Retrieve"):
    try:
        # Khoảng thời gian bắt đầu và kết thúc trong ngày
        start_time = datetime.combine(selected_date, datetime.min.time())
        end_time = datetime.combine(selected_date, datetime.max.time())

        # Truy vấn theo timestamp hoặc CreatedAt
        query = {
            "$or": [
                {"timestamp": {"$gte": start_time, "$lte": end_time}},
                {"CreatedAt": {"$gte": start_time, "$lte": end_time}}
            ]
        }

        cursor = chatlog_collection.find(query).sort(
            [("timestamp", -1), ("CreatedAt", -1)]
        )

        # Chuyển sang DataFrame
        data = list(cursor)
        if not data:
            st.info("📭 Không có hội thoại nào trong ngày được chọn.")
        else:
            df = pd.DataFrame(data)

            # Chuẩn hóa hiển thị thời gian
            for field in ["timestamp", "CreatedAt"]:
                if field in df.columns:
                    df[field] = pd.to_datetime(df[field], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

            st.success(f"✅ Đã tìm thấy {len(df)} cuộc hội thoại.")
            st.dataframe(df)
    except Exception as e:
        st.error(f"❌ Lỗi khi truy vấn dữ liệu: {e}")
