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
from typing import Optional 
import pandas as pd
import json

# Print the current working directory
current_directory = os.getcwd()

# Load SBERT model for embeddings
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
score_collection = db["diemchuan"]

# Load OpenAI API Key
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Helper to get user IP
def get_user_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return "unknown"
        
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

# Load data from diemchuan collection into DataFrame
def load_score_data():
    data = list(score_collection.find({}, {"_id": 0}))
    return pd.DataFrame(data)

# Extract score, type and field name from user input
def parse_user_input(user_input: str) -> dict:
    score_match = re.search(r"\b(\d{1,2}(?:\.\d)?)\b", user_input)
    type_match = re.search(r"(thpt|học bạ)", user_input, re.IGNORECASE)
    field_match = re.search(r"ngành\s+(.+?)(?:\s+năm|\?|$)", user_input, re.IGNORECASE)

    extracted = {
        "score": float(score_match.group(1)) if score_match else None,
        "score_type": type_match.group(1).strip().lower() if type_match else None,
        "field": field_match.group(1).strip() if field_match else None
    }
    return extracted

# Search score database
def find_matching_scores(df, score_type: str, field: Optional[str], score: float):
    score_type = score_type.lower()
    if field:
        filtered = df[
            (df["ScoreType"].str.lower() == score_type) &
            (df["Field"].str.lower().str.contains(field.lower()))
        ]
        results = []
        for year in [2023, 2024, 2025]:
            rows = filtered[filtered["Year"] == year]
            for _, row in rows.iterrows():
                passing_score = float(row["Score"])
                status = "✔️ Đủ điểm" if score >= passing_score else "❌ Không đủ điểm"
                results.append({
                    "Year": year,
                    "Field": row["Field"],
                    "Score": passing_score,
                    "Status": status
                })
        return results
    else:
        # Nếu không có ngành cụ thể, tìm mọi ngành có điểm chuẩn <= điểm người dùng
        filtered = df[
            (df["ScoreType"].str.lower() == score_type) &
            (df["Year"].isin([2024, 2025])) &
            (df["Score"] <= score)
        ]
        return filtered[["Field", "Year", "Score"]].to_dict(orient="records")

def classify_and_extract_user_query(user_query: str):
    system_prompt = """
Bạn là hệ thống phân loại và trích xuất thông tin từ câu hỏi tuyển sinh của thí sinh.
1. Nếu câu hỏi là loại "hỏi về cộng điểm" hoặc "tính điểm ưu tiên", hãy xuất ra JSON sau (nếu có):
{
  "query_type": "tinh_diem_uutien",
  "original_score": <số điểm thi>,
  "ielts_score": <điểm IELTS>,
  "good_grade_years": <số năm học sinh giỏi>,
  "region": <khu vực ưu tiên như KV1, KV2, KV2-NT, KV3>
}
2. Nếu câu hỏi là loại "em được XX điểm học bạ có đỗ vào ngành ... không?", hãy xuất ra JSON sau:
{
  "query_type": "du_doan_do_nganh",
  "field": "<tên ngành>",
  "score_type": "<thpt or học bạ>",
  "score": <số điểm của thí sinh>
}
3. Nếu không nhận diện được, trả về:
{
  "query_type": "unknown"
}
Chỉ trả về kết quả JSON hợp lệ, không giải thích thêm.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
    )
    content = response.choices[0].message.content.strip()    
    st.write(content)
    # Try to parse dictionary content
    try:
        parsed = eval(content, {"__builtins__": None}, {})
        if isinstance(parsed, dict):
            # If already flattened with expected keys
            if "query_type" in parsed and "score_type" in parsed:
                return {
                    "query_type": parsed["query_type"],
                    "extracted": {
                        "field": parsed.get("field"),
                        "score_type": parsed.get("score_type"),
                        "score": parsed.get("score")
                    }
                }
            elif "query_type" in parsed and "extracted" in parsed:
                return parsed
    except Exception:
        pass    
    return {"query_type": "unknown", "extracted": {}}
        
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

def combine_all_document_texts():
    # Combine all document texts into a single string as context
    combined_context = "\n\n".join([doc["content"] for doc in documents])
    return combined_context

def preview_documents(documents):
    for i, doc in enumerate(documents):
        content_words = doc["content"].split()
        preview = " ".join(content_words[:100])
        st.write(f"### Document {i + 1} Preview")
        st.write(preview)

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

# Function to find the best FAQ matches
def find_best_faq_matches(user_query, top_k=3):
    query_embedding = sbert_model.encode([user_query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idxs = faiss_faq_index.search(query_embedding, top_k)

    best_matches = [faq_data[idx] for idx in best_match_idxs[0]]
    similarities = [
        util.cos_sim(query_embedding, faq_embeddings[idx]).item()
        for idx in best_match_idxs[0]
    ]

    return best_matches, similarities

# Function to retrieve the most relevant document chunk
def retrieve_best_chunk(query, max_tokens=500):
    """
    Retrieves the most relevant document chunks by:
    1. Searching for exact keyword matches and extracting 300-token snippets.
    2. Using FAISS to find the most semantically relevant chunk.
    3. Combining both results for a comprehensive context.
    """
    if not faiss_index or not chunked_texts:
        return None, "No documents found."

    # Convert query to lowercase for case-insensitive search
    query_lower = query.lower()
    
    # 1️⃣ Keyword-based search
    keyword_snippets = []
    for doc in documents:
        words = doc["content"].split()
        
        # Find all keyword occurrences
        matches = [m.start() for m in re.finditer(re.escape(query_lower), doc["content"].lower())]

        for match_idx in matches:
            # Convert match index to word index
            word_idx = len(doc["content"][:match_idx].split())

            # Extract 150 tokens around the match
            start_idx = max(0, word_idx - 10)
            end_idx = min(len(words), word_idx + 140)

            snippet = " ".join(words[start_idx:end_idx])
            keyword_snippets.append(snippet)

    # Combine keyword snippets into a single string
    keyword_context = "\n\n".join(keyword_snippets)

    # 2️⃣ FAISS-based retrieval
    query_embedding = sbert_model.encode([query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idxs = faiss_index.search(query_embedding, 1)  # Retrieve top-1 chunk

    best_chunk = chunked_texts[best_match_idxs[0][0]]
    best_doc_title = chunked_titles[best_match_idxs[0][0]]

    # Find full document that contains this chunk
    best_doc = next((doc for doc in documents if doc["title"] == best_doc_title), None)
    
    if not best_doc:
        return None, "No relevant document found."

    # Extract 1000 tokens around the best chunk
    faiss_context = extract_relevant_text(best_doc["content"], best_chunk, max_tokens=max_tokens)

    # 3️⃣ Combine keyword-based and FAISS-based contexts
    final_context = f"{keyword_context}\n\n{faiss_context}".strip()

    return best_doc, final_context


# Function to extract up to 1000 tokens around the best chunk
def extract_relevant_text(full_text, best_chunk, max_tokens=500):
    words = full_text.split()
    chunk_words = best_chunk.split()

    match_start = None
    for i in range(len(words) - len(chunk_words) + 1):
        if words[i:i + len(chunk_words)] == chunk_words:
            match_start = i
            break

    if match_start is None:
        return best_chunk

    start_idx = max(0, match_start - (max_tokens // 2))
    end_idx = min(len(words), match_start + (max_tokens // 2))

    extracted_text = " ".join(words[start_idx:end_idx])
    return extracted_text

def estimate_token_count(text):
    # Using a simple tokenization method (split by spaces and punctuation)
    return len(text.split())
    
# Function to generate a response using GPT-4o with combined FAQ + document context
def generate_gpt_response(question, context):
    max_token_limit = 7000
    estimated_token_count = estimate_token_count(context)
    if estimated_token_count > max_token_limit:
        context = " ".join(context.split()[:max_token_limit])  # Cut off the context to the first 8000 tokens
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên thông tin sau đây, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện. "
        f"Dẫn nguồn từ nội dung có sẵn nếu cần.\n\n"
        f"Ngữ cảnh từ tài liệu:\n{context}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích, chỉ dựa trên nội dung đã cung cấp."},
                {"role": "user", "content": prompt}
            ]
            #,max_tokens=3000,
            #temperature=0.7
        )
        # Extract the response and the token usage
        generated_answer = response.choices[0].message.content.strip()
        #st.write(generated_answer)
        #generated_answer2 = response['choices'][0]['message']['content'].strip()  
        #st.write(generated_answer2)
        
        # Get token usage details
        #token_usage = response['usage']
        #input_tokens = token_usage['prompt_tokens']
        #output_tokens = token_usage['completion_tokens']
        #total_tokens = input_tokens + output_tokens

        # Log the token usage
        #st.write(f"Tokens used: Input = {input_tokens}, Output = {output_tokens}, Total = {total_tokens}")
        
        #return generated_answer, input_tokens, output_tokens, total_tokens
        return generated_answer

    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}", 0, 0, 0


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

    parsed=classify_and_extract_user_query(user_input)
    query_type = parsed.get("query_type")
    st.write(query_type)
    st.write(parsed["extracted"])
    if query_type == "du_doan_do_nganh":
        score = parsed["extracted"].get("score")
        field = parsed["extracted"].get("field")
        score_type = parsed["extracted"].get("score_type")
        # Handle predicted admission logic here
        df = load_score_data()
        if score is not None:
            generated_answer="Quá trình tư vấn điểm đầu vào cho thí sinh."
            if score_type is None:
                st.warning("❗ Vui lòng nhập lại câu hỏi kèm theo loại điểm (THPT hoặc học bạ). Bạn có thể hỏi: *Em được 25 điểm THPT, liệu có đỗ ngành Công nghệ thông tin không ạ?*")
            else:
                if field:
                    st.info(f"🔍 Tra cứu điểm ngành **{field}**, loại điểm **{score_type}**, điểm của bạn: **{score}**")
                    results = find_matching_scores(df, score_type, field, score)
                    if results:
                        for item in results:
                            eyear = item["Year"]
                            efield = item["Field"]
                            escore = item["Score"]
                            estatus = item["Status"]
                            st.write(f"- Năm {eyear} | Ngành: **{efield}** | Điểm chuẩn: **{escore}** → {estatus}")
                    else:
                        st.warning("Không tìm thấy thông tin điểm chuẩn phù hợp.")
                else:
                    st.info(f"🔍 Đang tra cứu các ngành phù hợp với điểm **{score}**, loại điểm **{score_type}**...")
                    matches = find_matching_scores(df, score_type, field=None, score=score)
                    if matches:
                        matches_df = pd.DataFrame(matches)
                        st.write("### ✅ Các ngành bạn có thể đủ điều kiện xét tuyển:")
                        st.dataframe(matches_df)
                    else:
                        st.warning("Không có ngành nào phù hợp với mức điểm này.")   
    elif query_type == "tinh_diem_uutien":
        ielts_score = parsed["extracted"].get("ielts_score")
        good_years = parsed["extracted"].get("good_grade_years")
        region = parsed["extracted"].get("region")
        # Handle bonus point calculation here

    #Tra cuu diem chuan
    #parsed = parse_user_input(user_input)
    else:
        # Retrieve FAQ-based responses
        best_faq_matches, faq_similarities = find_best_faq_matches(user_input)
        faq_context = ""
        for i, similarity in enumerate(faq_similarities):
            if similarity > 0.6:
                faq_context += f"Q: {best_faq_matches[i]['Question']}\nA: {best_faq_matches[i]['Answer']}\n\n"
    
        # Retrieve document-based context
        doc_context = retrieve_best_chunk(user_input)[1] if best_faq_matches else ""
    
        # Combine FAQ context and document context
        final_context = f"{faq_context}\n\n{doc_context}" if faq_context else doc_context
        #st.write(final_context)
        # Generate response with GPT
        #generated_answer, input_tokens, output_tokens, total_tokens = generate_gpt_response(user_input, final_context)
        generated_answer = generate_gpt_response(user_input, final_context)
        # Display the response
        with st.chat_message("assistant"):
            st.success("💡 **Câu trả lời:**")
            st.write(generated_answer)
            
        # Append conversation to session history
        st.session_state["chat_history"].append({"user": user_input, "bot": generated_answer})

    # Log to MongoDB
    chatlog_entry = {
        "user_ip": get_user_ip(),
        "timestamp": datetime.now(pytz.timezone("UTC")),
        "user_message": user_input,
        "bot_response": generated_answer,
        "is_good": True,
        "problem_detail": ""
    }
    chatlog_collection.insert_one(chatlog_entry)
