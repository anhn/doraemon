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
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import spacy

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

# Initialize NLTK and SpaCy for text preprocessing
stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()
nlp = spacy.load("en_core_web_sm")

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

# Function to clean and preprocess user query
def preprocess_user_query(query):
    # Convert to lowercase
    query = query.lower()

    # Remove stopwords using NLTK
    words = query.split()
    words = [word for word in words if word not in stop_words]

    # Lemmatize the query to get root words using WordNetLemmatizer
    lemmatized_query = " ".join([lemmatizer.lemmatize(word) for word in words])

    # Use SpaCy's NER to extract named entities for better search
    doc = nlp(lemmatized_query)
    entities = [ent.text for ent in doc.ents]
    
    # Optionally: Expand the query using synonyms (can be done through a thesaurus or pre-trained embeddings)

    return lemmatized_query, entities

# Function to optimize FAQ search based on query expansion
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

    # Preprocess the query (lemmatization, NER)
    processed_query, entities = preprocess_user_query(query)
    processed_query_embedding = sbert_model.encode([processed_query], convert_to_tensor=True).cpu().numpy()

    # 1️⃣ Keyword-based search (Semantic Search - Optimize for RAG)
    keyword_snippets = []
    faiss_index.search(processed_query_embedding, len(chunked_texts)) # Get all similarities for better keyword ranking
    
    # Ranking based on similarity to ensure keyword match is meaningful
    keyword_snippets.extend([chunk for i, chunk in enumerate(chunked_texts) if util.cos_sim(processed_query_embedding, doc_embeddings[i]).item() > 0.5])

    # 2️⃣ FAISS-based retrieval
    _, best_match_idxs = faiss_index.search(processed_query_embedding, 1)  # Retrieve top-1 chunk

    best_chunk = chunked_texts[best_match_idxs[0][0]]
    best_doc_title = chunked_titles[best_match_idxs[0][0]]

    # Find full document that contains this chunk
    best_doc = next((doc for doc in documents if doc["title"] == best_doc_title), None)
    
    if not best_doc:
        return None, "No relevant document found."

    # Extract relevant text around the best chunk
    faiss_context = extract_relevant_text(best_doc["content"], best_chunk, max_tokens=max_tokens)

    # 3️⃣ Combine keyword-based and FAISS-based contexts
    final_context = f"{' '.join(keyword_snippets)}\n\n{faiss_context}".strip()

    return best_doc, final_context


# Function to generate a response using GPT-4o with combined FAQ + document context
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
