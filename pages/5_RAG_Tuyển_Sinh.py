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
#def parse_user_input(user_input: str) -> dict:
#    score_match = re.search(r"\b(\d{1,2}(?:\.\d)?)\b", user_input)
#    type_match = re.search(r"(thpt|học bạ)", user_input, re.IGNORECASE)
#    field_match = re.search(r"ngành\s+(.+?)(?:\s+năm|\?|$)", user_input, re.IGNORECASE)
#
#    extracted = {
#        "score": float(score_match.group(1)) if score_match else None,
#        "score_type": type_match.group(1).strip().lower() if type_match else None,
#        "field": field_match.group(1).strip() if field_match else None
#    }
#    return extracted

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
1. Nếu câu hỏi là loại "cộng điểm học bạ" hoặc "tính điểm ưu tiên học bạ" hoặc "tổng điểm thưởng", "tổng điểm ưu tiên", dựa vào thông tin sau: 
Region: KV1 (miền núi, vùng núi, ven biển, hải đảo, biên giới, các thôn đặc biệt khó khăn, xã an toàn khu, ...), KV2-NT (khu vực nông thôn không thuộc KV1), KV2 (các thị xã, thành phố trực thuộc tỉnh; các thị xã, huyện ngoại thành ), KV3 (quận nội thành, thành phố).
Policy: UT1 hoặc UT2
hãy xuất ra JSON sau (nếu có):
{
  "query_type": "tinh_diem_hoc_ba_uutien",
  "original_score": <số điểm thi>,
  "ielts_score": <điểm IELTS>,
  "good_grade_years": <số năm học sinh giỏi>,
  "region": <khu vực ưu tiên như KV1, KV2, KV2-NT, KV3>,
  "policy": <UT1, UT2>
}
2. Nếu câu hỏi là như:
"em được XX điểm học bạ có đỗ vào ngành ... không?", 
"em được XX điểm thi THPT có đỗ vào ngành ... không?", 
"XX điểm thpt đỗ gì ko ạ ?"
hãy xuất ra JSON sau:
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

    try:
        #parsed = eval(content, {"__builtins__": None}, {})
        parsed = json.loads(content)
        #st.write("Parsed:", parsed)
        if isinstance(parsed, dict):
            query_type = parsed.get("query_type", "unknown") 
            # Normalize output: always wrap in "extracted"
            if query_type == "du_doan_do_nganh":
                return {
                    "query_type": query_type,
                    "extracted": {
                        "field": parsed.get("field"),
                        "score_type": parsed.get("score_type"),
                        "score": parsed.get("score")
                    }
                }
            elif query_type == "tinh_diem_hoc_ba_uutien":
                return {
                    "query_type": query_type,
                    "extracted": {
                        "original_score": parsed.get("original_score"),
                        "ielts_score": parsed.get("ielts_score"),
                        "good_grade_years": parsed.get("good_grade_years"),
                        "region": parsed.get("region"),
                        "policy": parsed.get("policy")
                    }
                }
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON decode error: {e}")
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
    if query_type == "du_doan_do_nganh":
        score = parsed["extracted"].get("score")
        field = parsed["extracted"].get("field")
        score_type = parsed["extracted"].get("score_type")
        # Handle predicted admission logic here
        df = load_score_data()
        if score is not None:
            if score_type is None:
                warning_msg = (
                    "❗ Vui lòng nhập lại câu hỏi kèm theo loại điểm (THPT hoặc học bạ). "
                    "Bạn có thể hỏi: *Em được 25 điểm THPT, liệu có đỗ ngành Công nghệ thông tin không ạ?*"
                )
                st.warning(warning_msg)
                generated_answer = warning_msg
            else:
                if field:
                    st.info(f"🔍 Tra cứu điểm ngành **{field}**, loại điểm **{score_type}**, điểm của bạn: **{score}**")
                    results = find_matching_scores(df, score_type, field, score)
                    if results:
                        result_texts = []
                        for item in results:
                            eyear = item["Year"]
                            efield = item["Field"]
                            escore = item["Score"]
                            estatus = item["Status"]
                            result_text = f"- Năm {eyear} | Ngành: **{efield}** | Điểm chuẩn: **{escore}** → {estatus}"
                            #st.write(result_text)
                            result_texts.append(result_text)
                        generated_answer = "\n".join(result_texts)
                    else:
                        warning_msg = "⚠️ Không tìm thấy thông tin điểm chuẩn phù hợp cho ngành đã nhập."
                        st.warning(warning_msg)
                        generated_answer = warning_msg
                else:
                    st.info(f"🔍 Đang tra cứu các ngành phù hợp với điểm **{score}**, loại điểm **{score_type}**...")
                    matches = find_matching_scores(df, score_type, field=None, score=score)
                    if matches:
                        matches_df = pd.DataFrame(matches)
                        st.write("### ✅ Các ngành bạn có thể đủ điều kiện xét tuyển:")
                        st.dataframe(matches_df)
                        generated_answer = "✅ Một số ngành bạn có thể đủ điều kiện xét tuyển:\n" + "\n".join(
                            f"- {row['Field']} ({row['Score']} điểm, năm {row['Year']})"
                            for _, row in matches_df.iterrows()
                        )
                    else:
                        warning_msg = "⚠️ Không có ngành nào phù hợp với mức điểm này."
                        st.warning(warning_msg)
                        generated_answer = warning_msg
        else:
            warning_msg = "⚠️ Không phát hiện điểm trong câu hỏi. Vui lòng nhập điểm để tiếp tục tư vấn."
            st.warning(warning_msg)
            generated_answer = warning_msg

    elif query_type == "tinh_diem_hoc_ba_uutien":
        original_score = parsed["extracted"].get("original_score")
        ielts_score = parsed["extracted"].get("ielts_score")
        good_years = parsed["extracted"].get("good_grade_years")
        region = parsed["extracted"].get("region")
        policy = parsed["extracted"].get("policy")
    
        # Initialize bonuses
        bonus = 0.0
        priority_region = 0.0
        priority_policy = 0.0
        max_score = 30.0
    
        # Calculate bonus based on IELTS
        try:
            ielts_score = float(ielts_score) if ielts_score else None
            if ielts_score:
                if 4.5 <= ielts_score < 5.0:
                    bonus += 0.75
                elif 5.0 <= ielts_score < 6.0:
                    bonus += 1.0
                elif 6.0 <= ielts_score < 7.0:
                    bonus += 1.25
                elif ielts_score >= 7.0:
                    bonus += 1.5
        except:
            pass
    
        # Calculate bonus based on good grade years
        try:
            good_years = int(good_years) if good_years else None
            if good_years == 1:
                bonus += 0.3
            elif good_years == 2:
                bonus += 0.6
            elif good_years >= 3:
                bonus += 0.9
        except:
            pass
    
        # Calculate priority based on region
        region = str(region).strip().upper() if region else ""
        if region == "KV1":
            priority_region = 0.75
        elif region == "KV2-NT":
            priority_region = 0.5
        elif region == "KV2":
            priority_region = 0.25
        elif region == "KV3":
            priority_region = 0.0
    
        # Calculate priority based on policy group
        policy = str(policy).strip().upper() if policy else ""
        if policy == "UT1":
            priority_policy = 2.0
        elif policy == "UT2":
            priority_policy = 1.0
    
        total_priority = priority_region + priority_policy
    
        # Final calculation
        if not original_score:
            total_added = round(bonus + total_priority, 2)
            generated_answer = (
                f"✅ Bạn được cộng tổng cộng **{total_added} điểm**.\n\n"
                f"- Điểm cộng thưởng: **{bonus}**\n"
                f"- Điểm ưu tiên khu vực: **{priority_region}**\n"
                f"- Điểm ưu tiên đối tượng chính sách: **{priority_policy}**\n\n"
                f"➡️ Bạn có thể cộng thêm vào điểm học bạ khi xét tuyển theo phương thức học bạ kết hợp."
            )
        else:
            try:
                original_score = float(original_score)
                combined_score = original_score + bonus
    
                if combined_score >= max_score:
                    final_score = max_score
                    adjusted_total_priority = 0
                elif combined_score >= 22.5:
                    adjusted_total_priority = round(((max_score - combined_score) / 7.5) * total_priority, 2)
                    final_score = round(combined_score + adjusted_total_priority, 2)
                else:
                    adjusted_total_priority = total_priority
                    final_score = round(combined_score + total_priority, 2)
    
                generated_answer = (
                    f"✅ Điểm xét tuyển của bạn sau khi cộng:\n"
                    f"- Điểm học bạ ban đầu: **{original_score}**\n"
                    f"- Điểm cộng thưởng: **{bonus}**\n"
                    f"- Điểm ưu tiên khu vực: **{priority_region}**\n"
                    f"- Điểm ưu tiên chính sách: **{priority_policy}**\n"
                    f"- Tổng điểm ưu tiên được cộng: **{adjusted_total_priority}**\n\n"
                    f"➡️ **Tổng điểm xét tuyển: {final_score}** (tối đa 30 điểm)"
                )
            except:
                generated_answer = "⚠️ Lỗi khi tính điểm xét tuyển. Vui lòng kiểm tra lại điểm đầu vào."

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
