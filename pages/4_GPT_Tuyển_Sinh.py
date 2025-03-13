import streamlit as st
import os
from openai import OpenAI
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, util
from pymongo import MongoClient
from datetime import datetime
from streamlit_feedback import streamlit_feedback
import requests
import uuid
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load SBERT model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]  # Load MongoDB URI from secrets
PERPLEXITY_API = st.secrets["perplexity"]["key"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
METAINFO_COLLECTION = "metainfo"
VIECLAM_COLLECTION = "ts24_vieclam"
CHATLOG_COLLECTION = "chatlog"

# Load OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-4-turbo"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
metainfo_collection = db[METAINFO_COLLECTION]
vieclam_collection = db[VIECLAM_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]

context_string = """ĐỀ ÁN TUYỂN SINH  NĂM 2024
"""
def get_ip():
    try:
        return requests.get("https://api64.ipify.org?format=json").json()["ip"]
    except:
        return "Unknown"

user_ip = get_ip()
       
# Initialize chat history in session state
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

# Set OpenAI API Key in the environment
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def load_faq_data():
    # Fetch data from all three collections, selecting only 'Question' and 'Answer' fields
    faq_data = list(faq_collection.find({}, {"_id": 0, "Question": 1, "Answer": 1}))
    return faq_data


faq_questions = [item["Question"] for item in load_faq_data()]
faq_embeddings = sbert_model.encode(faq_questions, convert_to_tensor=True).cpu().numpy()
# Build FAISS index
faiss_index = faiss.IndexFlatL2(faq_embeddings.shape[1])
faiss_index.add(faq_embeddings)

# Initialize session state for selection tracking
if "selected_question" not in st.session_state:
    st.session_state["selected_question"] = None
    st.session_state["selected_answer"] = None
    st.session_state["selected_similarity"] = None
	
def find_best_match(user_query):
    query_embedding = sbert_model.encode([user_query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idxs = faiss_index.search(query_embedding, 3)
    
    # Get best matches from FAISS
    best_matches_faiss = [load_faq_data()[idx] for idx in best_match_idxs[0]]
    # Compute similarity scores
    faiss_similarities = [
        util.cos_sim(query_embedding, faq_embeddings[idx]).item()
        for idx in best_match_idxs[0]
    ]
    for i in range(3):
        if st.button(f"🔹 {best_matches_faiss[i]['Question']} (Similarity: {faiss_similarities[i]:.4f})", key=f"btn_{i}"):
            st.session_state["selected_question"] = best_matches_faiss[i]["Question"]
            st.session_state["selected_answer"] = best_matches_faiss[i]["Answer"]
            st.session_state["selected_similarity"] = faiss_similarities[i]
            st.rerun()
	
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
        for message in response:
            content = message.choices[0].delta.content
            if content:  # Some parts may be None, skip them
                yield content
    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}"

def reformat_answer(answer):
    prompt = (
        f"Câu trả lời gốc: {answer}\n\n"
        f"Vui lòng mở rộng và diễn đạt lại câu trả lời trên một cách tự nhiên, đầy đủ, với giọng văn của một tư vấn viên nữ thân thiện và chuyên nghiệp."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một tư vấn viên tuyển sinh đại học chuyên nghiệp, có giọng điệu thân thiện và hỗ trợ."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        for message in response:
            content = message.choices[0].delta.content
            if content:  # Some parts may be None, skip them
                yield content
    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}"
	    
# Function to save chat logs to MongoDB
def save_chat_log(user_ip, user_message, bot_response, feedback):
    """Stores chat log into MongoDB, grouped by user IP"""
    if feedback and feedback.strip():
        chat_entry = {
                "user_ip": user_ip,
                "timestamp": datetime.utcnow(),
                "user_message": user_message,
                "bot_response": bot_response,
                "is_good": False,
                "problem_detail": feedback
            }    
    else:    
        chat_entry = {
            "user_ip": user_ip,
            "timestamp": datetime.utcnow(),
            "user_message": user_message,
            "bot_response": bot_response,
            "is_good": True,
            "problem_detail" : ""
        }
    chatlog_collection.insert_one(chat_entry)
    
def stream_text(text):
    """Converts a string into a generator to work with `st.write_stream()`."""
    for word in text.split():
        yield word + " "  # Stream words with a space for a natural effect
        
# Banner Image (Replace with your actual image URL or file path)
BANNER_URL = "https://utt.edu.vn/uploads/images/site/1722045380banner-utt.png"  # Example banner image

st.markdown(
    f"""
    <style>
        .center {{
            text-align: center;
        }}
        .banner {{
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 450px; /* Adjust size as needed */
        }}
        .title {{
            font-size: 28px;
            font-weight: bold;
            color: #1E88E5; /* Education-themed blue */
            margin-top: 15px;
        }}
        .subtitle {{
            font-size: 18px;
            color: #333;
            margin-top: 5px;
        }}
    </style>

    <div class="center">
        <img class="banner" src="{BANNER_URL}">
        <p class="title">🎓 Hỗ trợ tư vấn tuyển sinh - UTT</p>
        <p class="subtitle">Hỏi tôi bất kỳ điều gì về tuyển sinh đại học!</p>
    </div>
    """,
    unsafe_allow_html=True
)

# **Chat Interface**
st.subheader("💬 Chatbot Tuyển Sinh")

# **Display Chat History**
for chat in st.session_state["chat_log"]:
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["bot"])
        
user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)	
    #best_match, similarity = find_best_match(user_input)
    st.session_state["chat_log"].append({"user": user_input, "bot": ""})
    st.warning(st.session_state['selected_question'])
    st.warning(st.session_state['selected_answer'])
    find_best_match(user_input)
    st.warning(st.session_state['selected_question'])
    st.warning(st.session_state['selected_answer'])
    # EXPERIMENT - OLD CODE IN SUBLIME Step 2: Ensure selected values exist before proceeding
    if "selected_question" in st.session_state and st.session_state["selected_question"]:
        st.session_state["chat_log"][-1]["bot"] = st.session_state["selected_answer"]  # Update the last entry with the bot's response
        st.success(f"**Selected Question:** {st.session_state['selected_question']}")
        st.success(f"**Answer:** {st.session_state['selected_answer']}")
        # Step 3: Ensure similarity is available
        selected_similarity = st.session_state.get("selected_similarity", None)
        if selected_similarity is None:
            st.warning("⚠️ Please select a question first!")
        else:
            selected_similarity = float(selected_similarity)  # Convert safely
            st.success(f"**Similarity Score:** {selected_similarity:.4f}")
            # Step 4: Decide whether to use GPT based on similarity
            threshold = 0.4
            use_gpt = selected_similarity < threshold
            response_stream = stream_text(st.session_state["selected_answer"])
            with st.chat_message("assistant"):
                bot_response_container = st.empty()
                bot_response = ""
                for chunk in response_stream:
                    bot_response += chunk
                    bot_response_container.write(bot_response)
                st.session_state["response"] = bot_response
            # Save chat history
            st.session_state["chat_log"].append(
                {"user": user_input, "bot": bot_response, "is_gpt": use_gpt}
            )
