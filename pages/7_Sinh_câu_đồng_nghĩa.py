import streamlit as st
import pandas as pd
from collections import Counter
import underthesea
import re
import tempfile

# Predefined synonym suggestion dictionary (expand as needed)
AUTO_SYNONYM_GROUPS = {
    "trụ sở": ["cơ sở", "địa điểm"],
    "cơ sở": ["trụ sở", "địa điểm"],
    "địa điểm": ["trụ sở", "cơ sở"],
    "tổ hợp": ["khối"],
    "khối": ["tổ hợp"],
    "chuẩn": ["đỗ"],
    "đỗ": ["chuẩn"],
    "tuyển sinh": ["nhập học", "thi tuyển"],
    "ngành": ["chuyên ngành", "môn học"],
    "xét tuyển": ["tuyển chọn", "chọn lọc"]
}

def suggest_synonyms(word):
    return ", ".join(AUTO_SYNONYM_GROUPS.get(word, []))

# Streamlit UI
st.title("📚 Tạo Danh Sách Từ Đồng Nghĩa Tuyển Sinh Tiếng Việt")
st.markdown("Tải lên file Excel chứa văn bản tiếng Việt. Ứng dụng sẽ trích xuất các từ liên quan đến tuyển sinh và đề xuất từ đồng nghĩa.")

uploaded_file = st.file_uploader("📂 Tải lên file Excel", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ File đã được tải lên thành công.")

        if st.button("🚀 Tạo bản đồ từ đồng nghĩa"):
            with st.spinner("🔄 Đang phân tích..."):
                corpus = ' '.join(df.astype(str).apply(lambda x: ' '.join(x), axis=1))
                tagged = underthesea.pos_tag(corpus)

                # Filter words with relevant POS tags
                keywords = [
                    word.lower() for word, tag in tagged
                    if tag in ["N", "Np", "V"] and len(word) > 2
                ]

                # Count frequency
                freq = Counter(keywords)
                common = freq.most_common(200)

                # Create DataFrame
                df_synonyms = pd.DataFrame(common, columns=["base_word", "frequency"])
                df_synonyms["suggested_synonyms"] = df_synonyms["base_word"].apply(suggest_synonyms)
                df_synonyms["user_synonyms"] = ""  # for user to fill

                st.success(f"✅ Đã trích xuất {len(df_synonyms)} từ khóa.")
                st.dataframe(df_synonyms.head(10))

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    df_synonyms.to_excel(tmp.name, index=False)
                    st.download_button(
                        label="📥 Tải về danh sách từ đồng nghĩa",
                        data=open(tmp.name, "rb").read(),
                        file_name="vietnamese_synonym_map_auto.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý file: {str(e)}")
