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

# Load FAQ Data
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
            st.success(f"**Câu trả lời:** {st.session_state.selected_answer}")
            st.write(st.session_state.selected_answer)

        # **Append to chat log**
        st.session_state["chat_log"].append(
            {"user": user_query, "bot": st.session_state.selected_answer, "is_gpt": False}
        )

        return  # **Exit the function early to avoid showing buttons**

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
    find_best_match(user_input)  # If similarity > 0.92, the function exits here.

    # **Only show the message & buttons if no answer was returned directly**
    if st.session_state.best_matches_faiss and st.session_state.selected_answer is None:
        st.info("🤖 **Có phải bạn muốn hỏi một trong các câu sau không?** Nếu không, phiền bạn gõ lại câu hỏi một cách tường minh.")

        # **Display Answer Buttons**
        for i in range(len(st.session_state.best_matches_faiss)):
            if st.button(
                f"🔹 {st.session_state.best_matches_faiss[i]['Question']} "
                f"(Similarity: {st.session_state.faiss_similarities[i]:.4f})",
                key=f"btn_{i}",
            ):
                st.session_state.selected_index = i  # Store selected index in session state
                st.experimental_rerun()  # **Force rerun to display answer**

# **Process Button Click**
if st.session_state.selected_index is not None:
    idx = st.session_state.selected_index
    st.session_state.selected_question = st.session_state.best_matches_faiss[idx]["Question"]
    st.session_state.selected_answer = st.session_state.best_matches_faiss[idx]["Answer"]

    # **Display Selected Answer**
    with st.chat_message("assistant"):
        st.success(f"**Selected Question:** {st.session_state.selected_question}")
        st.success(f"**Answer:** {st.session_state.selected_answer}")
        st.write(st.session_state.selected_answer)

    # **Append to chat log**
    st.session_state["chat_log"].append(
        {"user": user_input, "bot": st.session_state.selected_answer, "is_gpt": False}
    )

    # Reset selected_index after processing
    st.session_state.selected_index = None
