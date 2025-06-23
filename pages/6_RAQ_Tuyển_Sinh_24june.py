import streamlit as st
import os
import glob
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from pymongo import MongoClient
from docx import Document
import re
from datetime import datetime
import pytz
import requests

# Load SBERT model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"
client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]

# Load OpenAI API Key
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Get user IP

def get_user_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return "unknown"

# Load documents
@st.cache_data
def load_documents():
    docx_files = glob.glob("*.docx")
    documents = []
    chunked_texts = []
    chunked_titles = []

    for file in docx_files:
        try:
            doc = Document(file)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            words = text.split()
            for i in range(0, len(words), 384):
                chunk = " ".join(words[i:i+512])
                chunked_texts.append(chunk)
                chunked_titles.append(file)
            documents.append({"title": file, "content": text})
        except Exception as e:
            st.warning(f"Error reading {file}: {e}")

    return documents, chunked_texts, chunked_titles

documents, chunked_texts, chunked_titles = load_documents()

# Create FAISS index for documents
@st.cache_resource
def create_faiss_index():
    doc_embeddings = sbert_model.encode(chunked_texts, convert_to_tensor=True).cpu().numpy()
    index = faiss.IndexFlatL2(doc_embeddings.shape[1])
    index.add(doc_embeddings)
    return index

faiss_index = create_faiss_index()

# Load and embed FAQs with Q+A format
@st.cache_data
def load_faq():
    faq_data = list(faq_collection.find({}, {"_id": 0, "Question": 1, "Answer": 1}))
    faq_texts = [f"Q: {item['Question']}\nA: {item['Answer']}" for item in faq_data]
    faq_embeddings = sbert_model.encode(faq_texts, convert_to_tensor=True).cpu()
    return faq_data, faq_embeddings

faq_data, faq_embeddings = load_faq()

# Rerank FAQ using cosine similarity
def find_best_faq_matches(user_query, top_k=3):
    query_text = f"Q: {user_query}"
    query_embedding = sbert_model.encode([query_text], convert_to_tensor=True).cpu()
    cosine_scores = util.cos_sim(query_embedding, faq_embeddings)[0]
    top_indices = np.argpartition(-cosine_scores, range(top_k))[:top_k]
    sorted_idx = np.argsort(-cosine_scores[top_indices])
    reranked_indices = top_indices[sorted_idx]
    best_matches = [faq_data[i] for i in reranked_indices]
    similarities = [cosine_scores[i].item() for i in reranked_indices]
    return best_matches, similarities

# Retrieve best document chunk
def retrieve_best_chunk(query, max_tokens=500):
    query_embedding = sbert_model.encode([query], convert_to_tensor=True).cpu().numpy()
    _, indices = faiss_index.search(query_embedding, 1)
    best_chunk = chunked_texts[indices[0][0]]
    return best_chunk

# Estimate token count

def estimate_token_count(text):
    return len(text.split())

# Generate GPT response
def generate_gpt_response(question, context):
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên thông tin sau đây, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện."
        f"\n\nNgữ cảnh từ tài liệu:\n{context}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}"

# Streamlit App
st.title("📚 Trang Tư Vấn Tuyển Sinh")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(msg["user"])
    with st.chat_message("assistant"):
        st.write(msg["bot"])

user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    faq_matches, similarities = find_best_faq_matches(user_input)
    faq_context = "\n\n".join([f"Q: {m['Question']}\nA: {m['Answer']}" for m, sim in zip(faq_matches, similarities) if sim > 0.6])
    doc_context = retrieve_best_chunk(user_input)
    context = f"{faq_context}\n\n{doc_context}" if faq_context else doc_context
    response = generate_gpt_response(user_input, context)

    with st.chat_message("assistant"):
        st.success("💡 **Câu trả lời:**")
        st.write(response)

    st.session_state.chat_history.append({"user": user_input, "bot": response})

    chatlog_collection.insert_one({
        "user_ip": get_user_ip(),
        "timestamp": datetime.now(pytz.timezone("UTC")),
        "user_message": user_input,
        "bot_response": response,
        "is_good": True,
        "problem_detail": ""
    })
