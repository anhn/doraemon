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

# Function to generate a response using GPT-4o with combined FAQ + document context
def generate_gpt4o_response(question, context):
    """
    Generates a response using GPT-4o while incorporating previous chat history.
    """
    # Include previous chat history (last 5 exchanges for context)
    #chat_history_context = "\n\n".join(
    #    [f"User: {chat['user']}\nAssistant: {chat['bot']}" for chat in st.session_state["chat_history"][-5:]]
    #)
    # Combine chat history and retrieved context
    #combined_context = f"{chat_history_context}\n\n{context}".strip()
    #st.write(combined_context)
   # Construct prompt
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

    # Retrieve FAQ-based responses
    best_faq_matches, faq_similarities = find_best_faq_matches(user_input)

    faq_context = "\n\n".join(
        [f"Q: {match['Question']}\nA: {match['Answer']}" for match in best_faq_matches]
    ) if best_faq_matches else ""

    # Retrieve document-based context
    doc_context = retrieve_best_chunk(user_input)[1] if best_faq_matches else ""

    # Combine FAQ context and document context
    final_context = f"{faq_context}\n\n{doc_context}" if faq_context else doc_context

    # Generate response with GPT-4o
    generated_answer = generate_gpt4o_response(user_input, final_context)
    # Display response
    with st.chat_message("assistant"):
        st.success("💡 **Câu trả lời:**")
        st.write(generated_answer)

    # Append conversation to session history
    st.session_state["chat_history"].append({"user": user_input, "bot": generated_answer})
