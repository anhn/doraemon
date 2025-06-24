import streamlit as st
import pandas as pd
import itertools
import re
import torch
import tempfile
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from underthesea import word_tokenize
from pymongo import MongoClient
from openai import OpenAI
import os

# Load SBERT for embeddings if needed later
from sentence_transformers import SentenceTransformer

# === CONFIG ===
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"

# === Load from secrets ===
MONGO_URI = st.secrets["mongo"]["uri"]
OPENAI_API_KEY = st.secrets["api"]["key"]
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# MongoDB connection
client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]

# Load paraphrasing model
@st.cache_resource
def load_model():
    model_name = "VietAI/vit5-base-vietnews-summarization"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return tokenizer, model

tokenizer, model = load_model()

# Synonym groups
SYNONYM_GROUPS = [
    ["trụ sở", "cơ sở", "địa điểm"],
    ["tổ hợp", "khối"],
    ["chuẩn", "đỗ"],
]

def find_synonym_groups(question):
    present_groups = []
    for group in SYNONYM_GROUPS:
        if any(re.search(rf"\b{w}\b", question) for w in group):
            present_groups.append(group)
    return present_groups

def generate_synonym_variants(question):
    groups = find_synonym_groups(question)
    if not groups:
        return [question]
    combinations = list(itertools.product(*groups))
    variants = set()
    for combo in combinations:
        new_q = question
        for group, word in zip(groups, combo):
            for w in group:
                new_q = re.sub(rf"\b{w}\b", word, new_q)
        variants.add(new_q)
    return list(variants)

def paraphrase_question(question, num_return_sequences=1):
    input_text = "paraphrase: " + question
    inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=128, truncation=True)
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_length=128,
            num_return_sequences=num_return_sequences,
            do_sample=True,
            top_k=50,
            top_p=0.95,
            temperature=0.8,
        )
    return [tokenizer.decode(o, skip_special_tokens=True) for o in outputs]

def expand_question(question):
    all_variants = set()
    synonym_variants = generate_synonym_variants(question)
    for variant in synonym_variants:
        all_variants.add(variant)
        nlp_variants = paraphrase_question(variant, num_return_sequences=2)
        all_variants.update(nlp_variants)
    return list(all_variants)

# === Streamlit App ===
st.title("📚 Mở rộng câu hỏi tuyển sinh từ MongoDB")
st.markdown("Dữ liệu được lấy từ bộ sưu tập `faqtuyensinh`. Ứng dụng sẽ tạo thêm các biến thể của câu hỏi để hỗ trợ chatbot hoặc hệ thống tìm kiếm.")

if st.button("🚀 Lấy dữ liệu & Tạo biến thể"):
    with st.spinner("🔄 Đang truy vấn MongoDB và tạo biến thể..."):
        raw_data = list(faq_collection.find({}, {"_id": 0, "question": 1, "answer": 1}))
        expanded_rows = []

        for item in raw_data:
            question = str(item["question"]).strip()
            answer = str(item["answer"]).strip()
            variants = expand_question(question)
            for vq in variants:
                expanded_rows.append({"question": vq, "answer": answer})

        expanded_df = pd.DataFrame(expanded_rows).drop_duplicates()
        st.success(f"✅ Hoàn tất! Đã tạo {len(expanded_df)} cặp câu hỏi - trả lời.")
        st.dataframe(expanded_df.head(10))

        # Download button
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            expanded_df.to_excel(tmp.name, index=False)
            st.download_button(
                label="📥 Tải về file kết quả",
                data=open(tmp.name, "rb").read(),
                file_name="qa_expanded_from_mongo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
