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

# Print the current working directory
current_directory = os.getcwd()

# Load SBERT model for embeddings
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]

# Load OpenAI API Key
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Function to extract text from .docx files
def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"Error reading {docx_path}: {str(e)}"

# Function to split text into overlapping chunks
def split_text_into_chunks(text, chunk_size=512, overlap=128):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

# Load all .docx files from the current directory
@st.cache_data
def load_documents():
    docx_files = glob.glob(os.path.join(current_directory, "*.docx"))
    documents = []
    chunked_texts = []
    chunked_titles = []
    
    for file in docx_files:
        doc_text = extract_text_from_docx(file)
        if doc_text:
            chunks = split_text_into_chunks(doc_text)
            documents.append({"title": os.path.basename(file), "content": doc_text, "chunks": chunks})
            chunked_texts.extend(chunks)
            chunked_titles.extend([os.path.basename(file)] * len(chunks))  # Associate each chunk with its document

    return documents, chunked_texts, chunked_titles

documents, chunked_texts, chunked_titles = load_documents()

# Encode document chunks and create FAISS index
@st.cache_resource
def create_faiss_index():
    if not chunked_texts:
        return None
    doc_embeddings = sbert_model.encode(chunked_texts, convert_to_tensor=True).cpu().numpy()
    index = faiss.IndexFlatL2(doc_embeddings.shape[1])
    index.add(doc_embeddings)
    return index

faiss_index = create_faiss_index()

# Load FAQ Data
def load_faq_data():
    return list(faq_collection.find({}, {"_id": 0, "Question": 1, "Answer": 1}))

faq_data = load_faq_data()
faq_questions = [item["Question"] for item in faq_data]
faq_embeddings = sbert_model.encode(faq_questions, convert_to_tensor=True).cpu().numpy()

# Build FAISS index for FAQ search
faiss_faq_index = faiss.IndexFlatL2(faq_embeddings.shape[1])
faiss_faq_index.add(faq_embeddings)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Function to extract keywords using GPT
def extract_keywords_from_gpt(query):
    prompt = f"Extract the main keywords from the following query:\n{query}"
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Extract keywords from the input query."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.7
        )
        return response.choices[0].message.content.strip().split(",")  # Split by commas for keywords
    except Exception as e:
        return []

# Function to search for keywords and extract text around them
def extract_relevant_text_around_keywords(query_keywords, chunked_texts, max_tokens=200):
    extracted_texts = []
    for chunk in chunked_texts:
        words = chunk.split()
        relevant_text = []
        
        for keyword in query_keywords:
            if keyword.lower() in chunk.lower():
                # Find the position of the keyword in the chunk
                start_idx = max(0, chunk.lower().find(keyword.lower()) - max_tokens // 2)
                end_idx = min(len(words), chunk.lower().find(keyword.lower()) + len(keyword.split()) + max_tokens // 2)
                
                # Add the relevant text around the keyword
                relevant_text.append(" ".join(words[start_idx:end_idx]))
        
        if relevant_text:
            extracted_texts.append(" ".join(relevant_text))
    
    # Ensure 200 unique tokens
    all_relevant_text = " ".join(extracted_texts)
    unique_tokens = set(all_relevant_text.split())
    return " ".join(list(unique_tokens)[:max_tokens])

# Function to generate a response using GPT-4o with context
def generate_gpt4o_response(question, context):
    """
    Generates a response using GPT-4o while incorporating previous chat history.
    """
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên cuộc trò chuyện trước đó và thông tin sau đây, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện. "
        f"Dẫn nguồn từ nội dung có sẵn nếu cần.\n\n"
        f"Ngữ cảnh từ cuộc trò chuyện trước và tài liệu:\n{context}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích, chỉ dựa trên nội dung đã cung cấp."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}"

# Streamlit UI
st.title("📚 Trang Tư Vấn Tuyển Sinh")

# Display chat history from session state
for chat in st.session_state["chat_history"]:
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["bot"])

# User input
user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    # Extract keywords using GPT
    query_keywords = extract_keywords_from_gpt(user_input)

    # Search for keywords in document chunks and extract relevant text
    relevant_context = extract_relevant_text_around_keywords(query_keywords, chunked_texts)
    st.write(query_keywords)
    # Generate the response using GPT-4o with the relevant extracted context
    generated_answer = generate_gpt4o_response(user_input, relevant_context)
    
    # Display the response
    with st.chat_message("assistant"):
        st.success("💡 **Câu trả lời:**")
        st.write(generated_answer)

    # Append conversation to session history
    st.session_state["chat_history"].append({"user": user_input, "bot": generated_answer})
