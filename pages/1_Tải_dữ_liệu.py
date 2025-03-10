import streamlit as st
import pandas as pd
import os
from pymongo import MongoClient

MONGO_URI = st.secrets["mongo"]["uri"]  # Load MongoDB URI from secrets
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"
METAINFO_COLLECTION = "metainfo"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]
metainfo_collection = db[METAINFO_COLLECTION]

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Admin page for the UTT Tuyen sinh 👋")

# File uploader
uploaded_file = st.file_uploader("Upload an Excel file with FAQ data", type=["csv"])

if uploaded_file is not None:
    # Read the CSV file
    df = pd.read_csv(uploaded_file, encoding="utf-8",  delimiter=";")
    
    # Ensure required columns are present
    required_columns = {"Question", "Answer", "Type"}
    if not required_columns.issubset(df.columns):
        st.error(f"The uploaded file must contain the following columns: {required_columns}")
    else:
        # Filter only Type 1 entries
        df_filtered = df[df["Type"] == 1]
        
        # Show the first 10 rows
        st.subheader("Preview of Uploaded Data (First 10 Rows)")
        st.dataframe(df_filtered.head(10))
        
        # Convert DataFrame to list of dictionaries
        faq_data = df_filtered.drop(columns=["Type"]).to_dict(orient="records")
        
        # Button to save data to the database
        if st.button("Save to Database"):
            if faq_data:
                faq_collection.insert_many(faq_data)
                st.success(f"Successfully added {len(faq_data)} FAQs of Type 1 to the database.")
            else:
                st.warning("No valid Type 1 FAQs found in the uploaded file.")

# Display existing FAQ entries
st.subheader("Existing FAQs")
faqs = list(faq_collection.find({}, {"_id": 0}))
if faqs:
    st.table(pd.DataFrame(faqs))
else:
    st.write("No FAQs found in the database.")

# Button to save data to MongoDB
if st.button("Add Meta Info"):
    meta_data = [
        ("Tên cơ sở đào tạo là gì?", "TRƯỜNG ĐH CÔNG NGHỆ GIAO THÔNG VẬN TẢI"),
        ("Mã trường của cơ sở đào tạo là gì?", "GTA"),
        ("Địa chỉ trụ sở chính của trường là gì?", "Phường Đồng Tâm, Tp. Vĩnh Yên, Tỉnh Vĩnh Phúc"),
        ("Cơ sở đào tạo có những phân hiệu nào?", "Phân hiệu Hà Nội: 54 Triều Khúc, Thanh Xuân, Tp. Hà Nội; Trung tâm đào tạo Thái Nguyên: P. Tân Thịnh, Tp. Thái Nguyên, T. Thái Nguyên"),
        ("Trang thông tin điện tử của trường là gì?", "utt.edu.vn"),
        ("Fanpage Facebook của trường là gì?", "https://www.facebook.com/utt.vn"),
        ("Zalo của trường là gì?", "https://zalo.me/dhcngtvt"),
        ("Số điện thoại liên hệ tuyển sinh là gì?", "02435526713"),
        ("Tình hình việc làm của sinh viên sau tốt nghiệp như thế nào?", "Kết quả khảo sát cho thấy tỷ lệ sinh viên có việc làm sau 12 tháng từ khi tốt nghiệp được công khai trên trang: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html"),
        ("Phương thức tuyển sinh chính của trường trong 2 năm gần nhất là gì?", "Xét tuyển sử dụng kết quả thi tốt nghiệp THPT và xét tuyển kết hợp theo đề án riêng của Trường."),
        ("Điểm trúng tuyển của ngành Quản trị kinh doanh năm 2023 là bao nhiêu?", "28 (học bạ KH), 22.85 (THPT)"),
        ("Ngành Công nghệ kỹ thuật ô tô có tỷ lệ sinh viên có việc làm sau tốt nghiệp là bao nhiêu?", "96.15%"),
        ("Mức học phí dự kiến cho năm học 2024-2025 là bao nhiêu?", "470,000đ/1 tín chỉ cho chương trình đại trà, 1.5 lần mức này cho chương trình tăng cường ngoại ngữ."),
        ("Các phương thức xét tuyển của trường là gì?", "Xét tuyển thẳng, xét học bạ kết hợp, xét tuyển dựa trên điểm thi tốt nghiệp THPT, xét tuyển dựa trên điểm thi đánh giá tư duy."),
        ("Tổ hợp môn xét tuyển của trường gồm những tổ hợp nào?", "A00 (Toán, Lý, Hóa), A01 (Toán, Lý, Tiếng Anh), D01 (Toán, Văn, Tiếng Anh), D07 (Toán, Hóa, Tiếng Anh)."),
        ("Thời gian tuyển sinh đợt 1 năm 2024 của trường là khi nào?", "Từ ngày 15/3/2024 đến ngày 27/4/2024."),
        ("Chỉ tiêu tuyển sinh của ngành Logistics và quản lý chuỗi cung ứng năm 2024 là bao nhiêu?", "180 (học bạ KH), 70 (THPT)"),
        ("Trường có tuyển sinh theo phương thức nào khác không?", "Có, xét tuyển dựa trên điểm thi đánh giá tư duy do ĐH Bách khoa Hà Nội tổ chức."),
        ("Chính sách ưu tiên trong xét tuyển của trường là gì?", "Cộng điểm ưu tiên cho thí sinh đạt giải HSG cấp tỉnh/thành phố, có chứng chỉ IELTS ≥ 4.5, hoặc có thành tích học sinh giỏi."),
        ("Thời gian dự kiến tuyển sinh bổ sung nếu có là khi nào?", "Sau ngày 22/8/2024."),
    ]
    # Gán ID và type cho dữ liệu metadata
    metainfo_data = [{"ID": f"Q{str(i+1).zfill(3)}", "Question": item[0], "Answer": item[1], "Type": 1} for i, item in enumerate(meta_data)]
    metainfo_collection.insert_many(metainfo_data)
    st.success("Dữ liệu Metadata đã được lưu vào MongoDB thành công!")
