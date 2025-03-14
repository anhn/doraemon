import streamlit as st
import os
from openai import OpenAI
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, util
from pymongo import MongoClient
from datetime import datetime
import requests

# Load SBERT model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]

os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# Load FAQ Data
def generate_gpt4_response(question, context):
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên thông tin sau đây, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện. "
        f"Dẫn nguồn từ nội dung có sẵn nếu cần.\n\n"
        f"Thông tin: {context}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích, chỉ dựa trên nội dung đã cung cấp."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        return "".join([message.choices[0].delta.content for message in response if message.choices[0].delta.content])
    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}"
        
def load_faq_data():
    return list(faq_collection.find({}, {"_id": 0, "Question": 1, "Answer": 1}))

faq_data = load_faq_data()
faq_questions = [item["Question"] for item in faq_data]
faq_embeddings = sbert_model.encode(faq_questions, convert_to_tensor=True).cpu().numpy()

# Build FAISS index
faiss_index = faiss.IndexFlatL2(faq_embeddings.shape[1])
faiss_index.add(faq_embeddings)

# Initialize session state
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

if "best_matches_faiss" not in st.session_state:
    st.session_state["best_matches_faiss"] = []

if "faiss_similarities" not in st.session_state:
    st.session_state["faiss_similarities"] = []

if "selected_index" not in st.session_state:
    st.session_state["selected_index"] = None

if "selected_question" not in st.session_state:
    st.session_state["selected_question"] = None

if "selected_answer" not in st.session_state:
    st.session_state["selected_answer"] = None

if "last_user_input" not in st.session_state:
    st.session_state["last_user_input"] = None  # Stores the last user input

if "show_buttons" not in st.session_state:
    st.session_state["show_buttons"] = False  # Ensures buttons show when needed

# Function to find best match
def find_best_match(user_query):
    query_embedding = sbert_model.encode([user_query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idxs = faiss_index.search(query_embedding, 3)

    st.session_state.best_matches_faiss = [faq_data[idx] for idx in best_match_idxs[0]]
    st.session_state.faiss_similarities = [
        util.cos_sim(query_embedding, faq_embeddings[idx]).item()
        for idx in best_match_idxs[0]
    ]

    # **Check if the highest similarity is greater than 0.92**
    max_similarity = max(st.session_state.faiss_similarities)
    if max_similarity > 0.92:
        # Find the index of the best match
        best_idx = st.session_state.faiss_similarities.index(max_similarity)

        # Store the best match as the selected question
        st.session_state.selected_question = st.session_state.best_matches_faiss[best_idx]["Question"]
        st.session_state.selected_answer = st.session_state.best_matches_faiss[best_idx]["Answer"]

        # **Display Direct Answer**
        with st.chat_message("assistant"):
            st.success(f"**Câu hỏi khớp với độ chính xác cao:** {st.session_state.selected_question}")
            st.write(st.session_state.selected_answer)

        # **Append to chat log**
        st.session_state["chat_log"].append(
            {"user": user_query, "bot": st.session_state.selected_answer, "is_gpt": False}
        )

        st.session_state["show_buttons"] = False  # Hide buttons if direct answer is given
        return True  # **Indicate that an answer was found directly**
    
    st.session_state["show_buttons"] = True  # Show buttons if similarity < 0.92
    return False  # **Indicate that no direct match was found**

# **Chat Interface**
st.subheader("💬 Chatbot Tuyển Sinh")

# **Display Chat History**
for chat in st.session_state["chat_log"]:
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["bot"])

# **User Input Handling**
user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state["chat_log"].append({"user": user_input, "bot": ""})
    st.session_state["last_user_input"] = user_input  # Store user input for button selection

    found_answer = find_best_match(user_input)  # Returns True if similarity > 0.92

    # **Only show the message & buttons if no answer was returned directly**
    if not found_answer and st.session_state.best_matches_faiss:
        st.info("🤖 **Có phải bạn muốn hỏi một trong các câu sau không?** Nếu không, phiền bạn gõ lại câu hỏi một cách tường minh.")

# **Display Answer Buttons if Similarity < 0.92**
if st.session_state["show_buttons"] and st.session_state.best_matches_faiss:
    for i in range(len(st.session_state.best_matches_faiss)):
        if st.button(
            f"🔹 {st.session_state.best_matches_faiss[i]['Question']} "
            f"(Similarity: {st.session_state.faiss_similarities[i]:.4f})",
            key=f"btn_{i}",
        ):
            st.session_state.selected_index = i  # Store selected index in session state
            st.rerun()  # **Force rerun to display answer**
    
    # **New Button: Search via GPT-4**
    if st.button("🔍 Tìm qua Internet cho câu hỏi của bạn"):
        st.session_state.selected_question = st.session_state["last_user_input"]
        st.session_state.selected_answer = generate_gpt4_response(st.session_state["last_user_input"], "")

        with st.chat_message("assistant"):
            st.success(f"**Tìm kiếm trên Internet:** {st.session_state.selected_question}")
            st.success(f"**Câu trả lời:** {st.session_state.selected_answer}")
            st.write(st.session_state.selected_answer)

        st.session_state["chat_log"].append(
            {"user": st.session_state["last_user_input"], "bot": st.session_state.selected_answer, "is_gpt": True}
        )
        st.session_state["show_buttons"] = False
        st.rerun()
# **Process Button Click**
if st.session_state.selected_index is not None:
    idx = st.session_state.selected_index
    st.session_state.selected_question = st.session_state.best_matches_faiss[idx]["Question"]
    st.session_state.selected_answer = st.session_state.best_matches_faiss[idx]["Answer"]

    # **Display Selected Answer**
    with st.chat_message("assistant"):
        st.success(f"**Selected Question:** {st.session_state.selected_question}")
        st.write(st.session_state.selected_answer)

    # **Append to chat log**
    st.session_state["chat_log"].append(
        {"user": st.session_state["last_user_input"], "bot": st.session_state.selected_answer, "is_gpt": False}
    )

    # Reset session state
    st.session_state.selected_index = None
    st.session_state.selected_answer = None
    st.session_state.selected_question = None
    st.session_state["show_buttons"] = False  # Hide buttons after selecting an answer
