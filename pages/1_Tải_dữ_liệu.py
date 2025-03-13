import streamlit as st
import pandas as pd
import os
from pymongo import MongoClient
from datetime import datetime

MONGO_URI = st.secrets["mongo"]["uri"]  # Load MongoDB URI from secrets
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"
METAINFO_COLLECTION = "metainfo"
TS24_ViECLAM_COLLECTION = "ts24_vieclam"
TS24_CHITIEU_COLLECTION = "ts24_chitieu"
TS24_ADMISSION_COLLECTION = "ts24_admission"
TS24_CHITIEU_TRUNGCAP_COLLECTION = "ts24_chitieu_trungcap"
client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]
metainfo_collection = db[METAINFO_COLLECTION]
tuyensinh24_collection = db[TS24_ViECLAM_COLLECTION]
chitieu24_collection = db[TS24_CHITIEU_COLLECTION]
admission24_collection = db[TS24_ADMISSION_COLLECTION]
chitieu_trungcap_collection = db[TS24_CHITIEU_TRUNGCAP_COLLECTION]
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
#st.subheader("Existing FAQs")
#faqs = list(faq_collection.find({}, {"_id": 0}))
#if faqs:
#    st.table(pd.DataFrame(faqs))
#else:
#    st.write("No FAQs found in the database.")
if st.button("Add metainfo into FAQ"):
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
        ("Số chỉ tiêu tuyển sinh của ngành Quản trị kinh doanh là bao nhiêu?", "440"),
        ("Số sinh viên nhập học ngành Quản trị kinh doanh là bao nhiêu?", "391"),
        ("Số sinh viên tốt nghiệp ngành Quản trị kinh doanh là bao nhiêu?", "180"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Quản trị kinh doanh là bao nhiêu?", "90.24%"),
        ("Số chỉ tiêu tuyển sinh của ngành Thương mại điện tử là bao nhiêu?", "230"),
        ("Số sinh viên nhập học ngành Thương mại điện tử là bao nhiêu?", "204"),
        ("Số sinh viên tốt nghiệp ngành Thương mại điện tử là bao nhiêu?", "114"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Thương mại điện tử là bao nhiêu?", "96.04%"),
        ("Số chỉ tiêu tuyển sinh của ngành Tài chính - Ngân hàng là bao nhiêu?", "360"),
        ("Số sinh viên nhập học ngành Tài chính - Ngân hàng là bao nhiêu?", "334"),
        ("Số sinh viên tốt nghiệp ngành Tài chính - Ngân hàng là bao nhiêu?", "88"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Tài chính - Ngân hàng là bao nhiêu?", "93.41%"),
        ("Số chỉ tiêu tuyển sinh của ngành Kế toán là bao nhiêu?", "410"),
        ("Số sinh viên nhập học ngành Kế toán là bao nhiêu?", "477"),
        ("Số sinh viên tốt nghiệp ngành Kế toán là bao nhiêu?", "282"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Kế toán là bao nhiêu?", "92.51%"),
        ("Số chỉ tiêu tuyển sinh của ngành Hệ thống thông tin là bao nhiêu?", "300"),
        ("Số sinh viên nhập học ngành Hệ thống thông tin là bao nhiêu?", "275"),
        ("Số sinh viên tốt nghiệp ngành Hệ thống thông tin là bao nhiêu?", "177"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Hệ thống thông tin là bao nhiêu?", "95.45%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ thông tin là bao nhiêu?", "630"),
        ("Số sinh viên nhập học ngành Công nghệ thông tin là bao nhiêu?", "634"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ thông tin là bao nhiêu?", "121"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ thông tin là bao nhiêu?", "91.38%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "290"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "261"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "101"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "94.85%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "270"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "201"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "156"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "94.15%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "250"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "290"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "168"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "91.95%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "320"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "364"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "162"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "92.65%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "510"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "489"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "520"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "96.15%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "250"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "267"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "98"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "93.81%"),
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "100"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "62"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "7"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "92.62%"),
        ("Số chỉ tiêu tuyển sinh của ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "350"),
        ("Số sinh viên nhập học ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "346"),
        ("Số sinh viên tốt nghiệp ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "113"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "96.63%"),
        ("Số chỉ tiêu tuyển sinh của ngành Kinh tế xây dựng là bao nhiêu?", "340"),
        ("Số sinh viên nhập học ngành Kinh tế xây dựng là bao nhiêu?", "262"),
        ("Số sinh viên tốt nghiệp ngành Kinh tế xây dựng là bao nhiêu?", "57"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Kinh tế xây dựng là bao nhiêu?", "95.38%"),
        ("Số chỉ tiêu tuyển sinh của ngành Khai thác vận tải là bao nhiêu?", "425"),
        ("Số sinh viên nhập học ngành Khai thác vận tải là bao nhiêu?", "425"),
        ("Số sinh viên tốt nghiệp ngành Khai thác vận tải là bao nhiêu?", "72"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Khai thác vận tải là bao nhiêu?", "100%")
    ]
    current_timestamp = datetime.utcnow()
    start_id_number = 54  # Corresponds to Q054
    # Transform data for MongoDB insertion
    chatlog_data = [
        {
            "ID": f"Q{start_id_number + index:03d}",  # Generates Q053, Q054, ..., Q072
            "Question": item[0],
            "Answer": item[1],
            "Type": 1,
            "CreatedTime": current_timestamp,
            "UpdatedTime": current_timestamp
        }
        for index, item in enumerate(meta_data)
    ]
    if chatlog_data:
        chatlog_collection.insert_many(chatlog_data)
        st.success("Data successfully inserted into chatlog.")
    else:
        st.warning("No data to insert.")

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

if st.button("Add Tinh Hinh Viec Lam - De An tuyen sinh 24"):
   qa_data_table = [
        ("Số chỉ tiêu tuyển sinh của ngành Quản trị kinh doanh là bao nhiêu?", "440"),
        ("Số sinh viên nhập học ngành Quản trị kinh doanh là bao nhiêu?", "391"),
        ("Số sinh viên tốt nghiệp ngành Quản trị kinh doanh là bao nhiêu?", "180"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Quản trị kinh doanh là bao nhiêu?", "90.24%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Thương mại điện tử là bao nhiêu?", "230"),
        ("Số sinh viên nhập học ngành Thương mại điện tử là bao nhiêu?", "204"),
        ("Số sinh viên tốt nghiệp ngành Thương mại điện tử là bao nhiêu?", "114"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Thương mại điện tử là bao nhiêu?", "96.04%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Tài chính - Ngân hàng là bao nhiêu?", "360"),
        ("Số sinh viên nhập học ngành Tài chính - Ngân hàng là bao nhiêu?", "334"),
        ("Số sinh viên tốt nghiệp ngành Tài chính - Ngân hàng là bao nhiêu?", "88"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Tài chính - Ngân hàng là bao nhiêu?", "93.41%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Kế toán là bao nhiêu?", "410"),
        ("Số sinh viên nhập học ngành Kế toán là bao nhiêu?", "477"),
        ("Số sinh viên tốt nghiệp ngành Kế toán là bao nhiêu?", "282"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Kế toán là bao nhiêu?", "92.51%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Hệ thống thông tin là bao nhiêu?", "300"),
        ("Số sinh viên nhập học ngành Hệ thống thông tin là bao nhiêu?", "275"),
        ("Số sinh viên tốt nghiệp ngành Hệ thống thông tin là bao nhiêu?", "177"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Hệ thống thông tin là bao nhiêu?", "95.45%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ thông tin là bao nhiêu?", "630"),
        ("Số sinh viên nhập học ngành Công nghệ thông tin là bao nhiêu?", "634"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ thông tin là bao nhiêu?", "121"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ thông tin là bao nhiêu?", "91.38%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "290"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "261"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "101"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật công trình xây dựng là bao nhiêu?", "94.85%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "270"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "201"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "156"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật giao thông là bao nhiêu?", "94.15%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "250"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "290"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "168"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật cơ khí là bao nhiêu?", "91.95%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "320"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "364"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "162"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật cơ điện tử là bao nhiêu?", "92.65%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "510"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "489"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "520"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật ô tô là bao nhiêu?", "96.15%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "250"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "267"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "98"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật điện tử - viễn thông là bao nhiêu?", "93.81%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "100"),
        ("Số sinh viên nhập học ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "62"),
        ("Số sinh viên tốt nghiệp ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "7"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Công nghệ kỹ thuật môi trường là bao nhiêu?", "92.62%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "350"),
        ("Số sinh viên nhập học ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "346"),
        ("Số sinh viên tốt nghiệp ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "113"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Logistics và quản lý chuỗi cung ứng là bao nhiêu?", "96.63%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Kinh tế xây dựng là bao nhiêu?", "340"),
        ("Số sinh viên nhập học ngành Kinh tế xây dựng là bao nhiêu?", "262"),
        ("Số sinh viên tốt nghiệp ngành Kinh tế xây dựng là bao nhiêu?", "57"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Kinh tế xây dựng là bao nhiêu?", "95.38%"),
        
        ("Số chỉ tiêu tuyển sinh của ngành Khai thác vận tải là bao nhiêu?", "425"),
        ("Số sinh viên nhập học ngành Khai thác vận tải là bao nhiêu?", "425"),
        ("Số sinh viên tốt nghiệp ngành Khai thác vận tải là bao nhiêu?", "72"),
        ("Tỷ lệ sinh viên có việc làm sau tốt nghiệp ngành Khai thác vận tải là bao nhiêu?", "100%") ]
    # Gán ID và type cho dữ liệu metadata
   tuyensinh24_data = [{"ID": f"Q24{str(i+1).zfill(3)}", "Question": item[0], "Answer": item[1], "Type": 1} for i, item in enumerate(qa_data_table)]
   tuyensinh24_collection.insert_many(tuyensinh24_data)
   st.success("Dữ liệu Tuyensinh 24 đã được lưu vào MongoDB thành công!")

if st.button("Add Chi Tieu Du kien 2024 - De An tuyen sinh 24"):
    qa_data_table = [
        ["7510104", "GTADCBC2", "Quản lý, khai thác và bảo trì đường cao tốc", 30, 10, 0],
        ["7510104", "GTADCBI2", "Mô hình thông tin công trình (BIM) trong dự án HTGT", 30, 10, 0],
        ["7510104", "GTADCCD1", "CNKT XD Cầu đường bộ (học tại Vĩnh Phúc)", 20, 20, 0],
        ["7510104", "GTADCCD2", "Công nghệ kỹ thuật XD Cầu đường bộ", 110, 20, 10],
        ["7510104", "GTADCCH2", "Hạ tầng giao thông đô thị thông minh", 20, 10, 0],
        ["7510201", "GTADCCK2", "Công nghệ kỹ thuật Cơ khí", 180, 60, 10],
        ["7510203", "GTADCCN2", "Công nghệ kỹ thuật cơ điện tử", 120, 40, 10],
        ["7510203", "GTADCCO2", "Công nghệ kỹ thuật cơ điện tử trên ô tô", 110, 30, 10],
        ["7510104", "GTADCCS2", "Xây dựng Cầu – đường sắt", 30, 10, 0],
        ["7510102", "GTADCDD2", "CNKT công trình XD dân dụng và công nghiệp", 200, 20, 10],
        ["7510104", "GTADCDS2", "CNKT xây dựng Đường sắt - Metro", 30, 10, 0],
        ["7510302", "GTADCDT2", "Công nghệ kỹ thuật điện tử - viễn thông", 130, 50, 0],
        ["7220201", "GTADCEN2", "Ngôn ngữ Anh", 50, 30, 0],
        ["7340201", "GTADCHL2", "Hải quan và Logistics", 80, 40, 0],
        ["7480104", "GTADCHT2", "Hệ thống thông tin", 120, 120, 10],
        ["7510102", "GTADCKN2", "Kiến trúc nội thất", 100, 40, 0],
        ["7340301", "GTADCKT1", "Kế toán doanh nghiệp (học tại Vĩnh Phúc)", 35, 10, 0],
        ["7340301", "GTADCKT2", "Kế toán doanh nghiệp", 300, 100, 30],
        ["7580301", "GTADCKX2", "Kinh tế xây dựng", 190, 80, 0],
        ["7380101", "GTADCLA2", "Luật", 30, 30, 0],
        ["7510605", "GTADCLG2", "Logistics và quản lý chuỗi cung ứng", 180, 70, 0],
        ["7510605", "GTADCLH2", "Logistics và hạ tầng giao thông", 40, 20, 0],
        ["7510406", "GTADCMN2", "Công nghệ và quản lý môi trường", 80, 20, 0],
        ["7510205", "GTADCOG2", "Công nghệ kỹ thuật ô tô và giao thông thông minh", 30, 10, 0],
        ["7510205", "GTADCOT1", "Công nghệ kỹ thuật Ô tô (học tại Vĩnh Phúc)", 30, 10, 0],
        ["7510205", "GTADCOT2", "Công nghệ kỹ thuật Ô tô", 250, 100, 20],
        ["7340101", "GTADCQM2", "Quản trị Marketing", 180, 60, 10],
        ["7340101", "GTADCQT2", "Quản trị doanh nghiệp", 150, 50, 10],
        ["7580302", "GTADCQX2", "Quản lý xây dựng", 60, 25, 0],
        ["7340122", "GTADCTD2", "Thương mại điện tử", 170, 70, 0],
        ["7480201", "GTADCTG2", "Trí tuệ nhân tạo và giao thông thông minh", 40, 10, 0],
        ["7340201", "GTADCTN2", "Tài chính doanh nghiệp", 170, 70, 0],
        ["7510104", "GTADCTQ2", "Thanh tra và quản lý công trình giao thông", 30, 10, 0],
        ["7480201", "GTADCTT1", "Công nghệ thông tin (học tại Vĩnh Phúc)", 25, 10, 0],
        ["7480201", "GTADCTT2", "Công nghệ thông tin", 300, 150, 15],
        ["7840101", "GTADCVL2", "Logistics và vận tải đa phương thức", 130, 50, 0],
        ["7510302", "GTADCVM2", "Công nghệ kỹ thuật vi mạch bán dẫn", 40, 20, 0],
        ["7840101", "GTADCVS2", "Quản lý và điều hành vận tải đường sắt", 20, 20, 0],
        ["7510102", "GTADCXQ2", "Xây dựng và quản lý hạ tầng đô thị", 60, 20, 0],
        ["7510605", "GTADKLG2", "Logistics - Trường Đại học Tongmyong - Hàn Quốc cấp bằng", 5, 5, 0],
        ["7480201", "GTADKTT2", "Công nghệ thông tin – ĐH Công nghệ thông tin và quản lý Ba Lan- UITM cấp bằng", 5, 5, 0],
        ["7510104", "GTADNCD2", "Công nghệ kỹ thuật xây dựng Cầu đường bộ (tăng cường tiếng Nhật, định hướng thực tập và làm việc tại Nhật Bản)", 10, 10, 0],
        ["7510302", "GTADNDT2", "Công nghệ kỹ thuật Điện tử - Viễn thông (tăng cường tiếng Nhật, định hướng thực tập và làm việc tại Nhật Bản)", 20, 10, 0],
        ["7510605", "GTADNLG2", "Logistics và quản lý chuỗi cung ứng (tăng cường tiếng Nhật, định hướng thực tập và làm việc tại Nhật Bản)", 20, 10, 0],
        ["7480201", "GTADNTT2", "Công nghệ thông tin (tăng cường tiếng Anh)", 10, 10, 0]
    ]
    # Gán ID và type cho dữ liệu metadata
    chitieu24_data = [
        {
            "ID": f"Q24{str(i+1).zfill(3)}",
            "FieldCodeStandard": row[0],
            "FieldCode": row[1],
            "FieldName": row[2],
            "TranscriptBasedAdmission": row[3],
            "SchoolScoreBasedAdmission": row[4],
            "CompetenceBasedAdmission": row[5],
            "Type": 1    
        }
        for i, row in enumerate(qa_data_table)
    ]
    chitieu24_collection.insert_many(chitieu24_data)
    st.success("Dữ liệu Chi Tieu 24 đã được lưu vào MongoDB thành công!")

if st.button("Add Admision 2024 - De An tuyen sinh 24"):
    admission_data = {
        "category": "Ngưỡng đầu vào",
        "methods": [
            {
                "name": "Phương thức tuyển thẳng",
                "description": "Theo quy chế tuyển sinh của Bộ GD&ĐT.",
                "criteria": None
            },
            {
                "name": "Phương thức xét học bạ kết hợp",
                "description": "Thí sinh có điểm tổ hợp môn xét tuyển >=18.0",
                "criteria": {
                    "semester_scores": ["Học kỳ 1 lớp 11", "Học kỳ 2 lớp 11", "Học kỳ 1 lớp 12"],
                    "min_score": 18.0
                }
            },
            {
                "name": "Phương thức xét tuyển dựa trên kết quả thi tốt nghiệp THPT năm 2024",
                "description": "Công bố sau khi có kết quả thi tốt nghiệp THPT năm 2024.",
                "criteria": None
            },
            {
                "name": "Phương thức xét tuyển dựa trên kết quả thi đánh giá tư duy",
                "description": "Thí sinh có tổng điểm thi đánh giá tư duy >= 50 điểm.",
                "criteria": {
                    "exam": "Thi đánh giá tư duy do Đại học Bách khoa Hà Nội tổ chức năm 2024",
                    "min_score": 50
                }
            },
            {
                "name": "Phương thức xét tuyển theo điểm thi THPT",
                "description": "Xét tuyển dựa trên điểm thi tốt nghiệp THPT năm 2024.",
                "exam_combinations": [
                    {"code": "A00", "subjects": ["Toán", "Vật lý", "Hóa học"]},
                    {"code": "A01", "subjects": ["Toán", "Vật lý", "Tiếng Anh"]},
                    {"code": "D01", "subjects": ["Toán", "Ngữ văn", "Tiếng Anh"]},
                    {"code": "D07", "subjects": ["Toán", "Hóa học", "Tiếng Anh"]}
                ],
                "score_difference": 0,
                "selection_criteria": [
                    "Ưu tiên thí sinh có thứ tự nguyện vọng nhỏ hơn nếu số lượng trúng tuyển lớn hơn chỉ tiêu.",
                    "Thí sinh được đăng ký không giới hạn nguyện vọng nhưng phải sắp xếp theo thứ tự ưu tiên.",
                    "Thí sinh chỉ trúng tuyển vào một nguyện vọng có mức ưu tiên cao nhất.",
                    "Xét tuyển theo ngành, lấy điểm từ cao xuống thấp đến khi hết chỉ tiêu.",
                    "Nếu phương thức xét tuyển không đạt chỉ tiêu, phần chỉ tiêu còn lại sẽ chuyển sang phương thức khác."
                ]
            },
            {
                "name": "Phương thức xét tuyển học bạ kết hợp (chi tiết tính điểm)",
                "description": "Tính điểm xét tuyển dựa trên học bạ THPT.",
                "scoring": {
                    "formula": "ĐXT = M0 + M1 + M2 + M3 + Điểm ưu tiên",
                    "details": {
                        "M0": "Tổng điểm quy đổi theo bảng quy đổi thang điểm 10 của điều kiện ưu tiên.",
                        "M1, M2, M3": "Điểm trung bình của 3 kỳ học lớp 11 và lớp 12.",
                        "priority_points": "Bao gồm điểm ưu tiên khu vực và đối tượng theo Quy chế tuyển sinh."
                    }
                },
                "tie_breaker": "Nếu ĐXT bằng điểm chuẩn, ưu tiên xét theo thứ tự nguyện vọng và điểm môn Toán.",
                "registration_method": "Đăng ký trực tuyến trên hệ thống xét tuyển của Trường & Bộ GD&ĐT.",
                "registration_periods": [
                    {"round": "Đợt 1", "start_date": "2024-03-15", "end_date": "2024-04-27"},
                    {"round": "Đợt 2", "start_date": "2024-05-03", "end_date": "2024-06-15"}
                ]
            },
            {
                "name": "Phương thức xét tuyển theo điểm thi đánh giá tư duy",
                "description": "Xét tuyển dựa trên điểm thi đánh giá tư duy do Đại học Bách khoa Hà Nội tổ chức.",
                "scoring": {
                    "formula": "ĐXT = Tổng điểm thi × 30 / 100 + Điểm ưu tiên",
                    "priority_points": "Bao gồm điểm ưu tiên khu vực và đối tượng theo Quy chế tuyển sinh."
                },
                "tie_breaker": "Ưu tiên xét tuyển theo tiêu chí thứ tự nguyện vọng."
            }
        ],
        "priority_policies": {
            "direct_admission": "Thực hiện theo quy định của Bộ Giáo dục và Đào tạo.",
            "academic_achievement_bonus": [
                {
                    "criteria": "Giải Nhất, Nhì, Ba kỳ thi học sinh giỏi cấp tỉnh/thành phố",
                    "bonus_points": {
                        "First Prize": 3.0,
                        "Second Prize": 2.0,
                        "Third Prize": 1.0
                    }
                },
                {
                    "criteria": "Chứng chỉ IELTS ≥ 4.5 (có thời hạn trong 24 tháng)",
                    "bonus_points": {
                        "IELTS 4.5-5.0": 1.0,
                        "IELTS 5.5": 1.5,
                        "IELTS 6.0": 2.0,
                        "IELTS 6.5": 2.5,
                        "IELTS 7.0-9.0": 3.0
                    }
                },
                {
                    "criteria": "Đạt học sinh giỏi trong các kỳ học",
                    "bonus_points": {
                        "1 kỳ": 0.3,
                        "2 kỳ": 0.6,
                        "3 kỳ": 0.9,
                        "4 kỳ": 1.2,
                        "5 kỳ": 1.5
                    }
                }
            ]
        }
    }
    # Insert into MongoDB
    admission24_collection.insert_one(admission_data)
    st.success("Dữ liệu nguong dau vao 24 đã được lưu vào MongoDB thành công!")

if st.button("Add Chi Tieu Tuyen Sinh cho Trung Cap - De An tuyen sinh 24"):
    quota_data = [
        {
            "category": "Chỉ tiêu tuyển sinh 2024 chính quy",
            "admission_requirements": {
                "eligible_candidates": "Thí sinh đã tốt nghiệp cao đẳng của Trường ĐH CNGTVT hoặc các trường Đại học, Cao đẳng khác có cùng ngành đào tạo.",
                "admission_scope": "Tuyển sinh trong cả nước",
                "admission_method": {
                    "type": "Xét tuyển",
                    "criteria": {
                        "total_score_required": "Tổng điểm môn cơ sở ngành và chuyên ngành, tổng điểm ≥ 11.0 (theo thang điểm 20)",
                        "selection_criteria": "Xét tuyển điểm lấy từ cao xuống thấp đến khi đủ chỉ tiêu. Điểm xét tuyển lấy đến 2 chữ số thập phân. Nếu nhiều hồ sơ có điểm xét tuyển bằng nhau thì lấy điểm môn cơ sở ngành."
                    }
                },
                "admission_schedule": {
                    "rounds_per_year": 4,
                    "months": ["Tháng 2", "Tháng 5", "Tháng 8", "Tháng 12"],
                    "application_submission": "Hồ sơ xét tuyển nộp tại Khoa Đào tạo tại chức",
                    "exam_subjects": ["Cơ sở ngành", "Chuyên ngành"]
                }
            },
            "tuition_and_fees": {
                "admission_fee": "Theo quy định",
                "tuition_fee": "Mức học phí năm học 2024-2025 thực hiện theo Nghị định 81/2021/NĐ-CP ngày 27/8/2021 của Chính phủ"
            },
            "priority_policies": "Xét tuyển thẳng; ưu tiên xét tuyển",
            "programs": [
                {
                    "education_level": "ĐH Liên thông",
                    "program_code": "7510104",
                    "program_name": "Công nghệ kỹ thuật giao thông",
                    "admission_method_code": "500",
                    "admission_method_name": "Sử dụng phương thức khác",
                    "quota": 60,
                    "document_number": "2872/QĐ-BGDĐT",
                    "issue_date": "15/05/2012",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2012
                },
                {
                    "education_level": "ĐH Liên thông",
                    "program_code": "7510102",
                    "program_name": "Công nghệ kỹ thuật công trình xây dựng",
                    "admission_method_code": "500",
                    "admission_method_name": "Sử dụng phương thức khác",
                    "quota": 60,
                    "document_number": "6368/QĐ-BGDĐT",
                    "issue_date": "26/09/2012",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2013
                },
                {
                    "education_level": "ĐH Liên thông",
                    "program_code": "7510205",
                    "program_name": "Công nghệ kỹ thuật ô tô",
                    "admission_method_code": "500",
                    "admission_method_name": "Sử dụng phương thức khác",
                    "quota": 60,
                    "document_number": "2872/QĐ-BGDĐT",
                    "issue_date": "15/05/2012",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2012
                },
                {
                    "education_level": "ĐH Liên thông",
                    "program_code": "7340301",
                    "program_name": "Kế toán",
                    "admission_method_code": "500",
                    "admission_method_name": "Sử dụng phương thức khác",
                    "quota": 30,
                    "document_number": "6368/QĐ-BGDĐT",
                    "issue_date": "26/09/2012",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2013
                }
            ]
        },
        {
            "category": "Chỉ tiêu tuyển sinh 2024 văn bằng hai",
            "admission_requirements": {
                "eligible_candidates": "Thí sinh đã tốt nghiệp đại học",
                "admission_scope": "Tuyển sinh trong cả nước",
                "admission_method": "Xét tuyển",
                "minimum_entry_requirement": "Đã có bằng tốt nghiệp đại học",
                "selection_criteria": "Xét tuyển điểm lấy từ cao xuống thấp đến khi đủ chỉ tiêu (căn cứ vào điểm TBC tốt nghiệp)",
                "admission_schedule": {
                    "rounds_per_year": 4,
                    "months": ["Tháng 2", "Tháng 5", "Tháng 8", "Tháng 12"],
                    "application_submission": "Hồ sơ xét tuyển nộp tại Khoa Đào tạo tại chức"
                }
            },
            "tuition_and_fees": {
                "admission_fee": "Theo quy định",
                "tuition_fee": "Mức học phí năm học 2024-2025 thực hiện theo Nghị định 81/2021/NĐ-CP ngày 27/8/2021 của Chính phủ"
            },
            "priority_policies": "Chính sách ưu tiên theo quy định",
            "programs": [
                {
                    "education_level": "ĐH Văn bằng 2",
                    "program_code": "7510104",
                    "program_name": "Công nghệ kỹ thuật giao thông",
                    "admission_method_code": "500",
                    "admission_method_name": "Phương thức khác",
                    "quota": 40,
                    "document_number": "4972/BGDĐT-GDĐH",
                    "issue_date": "05/10/2016",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2016
                },
                {
                    "education_level": "ĐH Văn bằng 2",
                    "program_code": "7510102",
                    "program_name": "Công nghệ kỹ thuật công trình xây dựng",
                    "admission_method_code": "500",
                    "admission_method_name": "Phương thức khác",
                    "quota": 40,
                    "document_number": "385/BGDĐT-GDĐH",
                    "issue_date": "30/01/2018",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2018
                },
                {
                    "education_level": "ĐH Văn bằng 2",
                    "program_code": "7510205",
                    "program_name": "Công nghệ kỹ thuật ô tô",
                    "admission_method_code": "500",
                    "admission_method_name": "Phương thức khác",
                    "quota": 20,
                    "document_number": "4972/BGDĐT-GDĐH",
                    "issue_date": "05/10/2016",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2016
                },
                {
                    "education_level": "ĐH Văn bằng 2",
                    "program_code": "7340301",
                    "program_name": "Kế toán",
                    "admission_method_code": "500",
                    "admission_method_name": "Phương thức khác",
                    "quota": 20,
                    "document_number": "4972/BGDĐT-GDĐH",
                    "issue_date": "05/10/2016",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2016
                },
                {
                    "education_level": "ĐH Văn bằng 2",
                    "program_code": "7580301",
                    "program_name": "Kinh tế xây dựng",
                    "admission_method_code": "500",
                    "admission_method_name": "Phương thức khác",
                    "quota": 30,
                    "document_number": "385/BGDĐT-GDĐH",
                    "issue_date": "30/01/2018",
                    "authorized_by": "Bộ Giáo dục và Đào tạo",
                    "start_year": 2018
                }
            ]
        }
    ]
    # Insert into MongoDB
    chitieu_trungcap_collection.insert_many(quota_data)
    st.success("Dữ liệu Chi Tieu 24 Trung Cap đã được lưu vào MongoDB thành công!")
