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

# Load SBERT model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]  # Load MongoDB URI from secrets
PERPLEXITY_API = st.secrets["perplexity"]["key"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"

# Load OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-4-turbo"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]

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
client = OpenAI(api_key=PERPLEXITY_API, base_url="https://api.perplexity.ai")


def load_faq_data():
    # Sample FAQ database
    faq_data = list(faq_collection.find({}, {"_id": 0}))
    return faq_data
# Convert FAQ questions to embeddings

faq_questions = [item["Question"] for item in load_faq_data()]
faq_embeddings = sbert_model.encode(faq_questions, convert_to_tensor=True).cpu().numpy()

# Build FAISS index
faiss_index = faiss.IndexFlatL2(faq_embeddings.shape[1])
faiss_index.add(faq_embeddings)

# Function to find best match using SBERT
def find_best_match(user_query):
    query_embedding = sbert_model.encode([user_query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idx = faiss_index.search(query_embedding, 1)
    best_match = load_faq_data()[best_match_idx[0][0]]
    # Compute similarity
    best_match_embedding = faq_embeddings[best_match_idx[0][0]]
    similarity = util.cos_sim(query_embedding, best_match_embedding).item()
    return best_match, similarity

    
# Function to generate GPT-4 response
def generate_gpt4_response(question, context):
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên thông tin tìm được trên internett, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện. Dẫn nguồn nếu có thể."
    )   
    try:
        response = client.chat.completions.create(
        model="sonar-pro",
        messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích."},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            max_tokens=3500  # Limit response length to ~250 words
        )
        for message in response:
            content = message.choices[0].delta.content
            if content:  # Some parts may be None, skip them
                yield content
    except Exception as e:
        return f"⚠️ Lỗi: {str(e)}"

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

if "response" not in st.session_state:
    st.session_state["response"] = None
user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    # Show user message
    with st.chat_message("user"):
        st.write(user_input)

    # Find best match in FAQ
    best_match, similarity = find_best_match(user_input)
    threshold = 0.7  # Minimum similarity to use FAQ answer
    # Extract and sanitize the answer field
    best_answer = best_match.get("Answer", "")
    print(best_answer)
    if isinstance(best_answer, float) and np.isnan(best_answer):
        best_answer = ""  # Replace NaN with empty string
    best_answer = str(best_answer)  # Convert non-string values to string
    use_gpt = similarity < threshold or best_answer.strip().lower() in [""]
    print(use_gpt)
    # Select response source
    if use_gpt:
        response_stream = generate_gpt4_response(user_input, best_match["Answer"])  # Now a generator
    else:
        response_stream = stream_text(best_match["Answer"])  # FAQ converted to a generator
    with st.chat_message("assistant"):
        bot_response_container = st.empty()  # Create an empty container
        bot_response = ""  # Collect the full response
        for chunk in response_stream:
            bot_response += chunk  # Append streamed content
            bot_response_container.write(bot_response)  # Update UI in real-time
        st.session_state["response"] = bot_response
        print(st.session_state["response"])

    # Save to session history
    st.session_state["chat_log"].append(
        {"user": user_input, "bot": bot_response, "is_gpt": use_gpt}
    )
    # Save chat log to MongoDB
    save_chat_log(user_ip, user_input, bot_response, feedback)
feedback=""
if st.session_state["response"]:
    feedback = streamlit_feedback(
        feedback_type="thumbs",
        optional_text_label="[Tùy chọn] Vui lòng giải thích",
    )
    if "feedback_value" not in st.session_state:
        st.session_state["feedback_value"] = None  # Default state
    if feedback and feedback != st.session_state["feedback_value"]:
        st.session_state["feedback_value"] = feedback  # Store feedback when changed
        print(feedback)  # Now, this will be executed
        # Retrieve the latest chat log entry for the current user
        last_chat = chatlog_collection.find_one(
            {"user_ip": user_ip},
            sort=[("timestamp", -1)]  # Get the latest entry by sorting timestamp descending
        )
        if last_chat:
            # Update the existing log with feedback details, user input, and bot response
            chatlog_collection.update_one(
                {"_id": last_chat["_id"]},  # Find the correct entry
                {
                    "$set": {
                        "is_good": False if feedback else True,
                        "problem_detail": feedback,
                        "user_message": user_input,  # Update user question
                        "bot_response": bot_response  # Update bot response
                    }
                }
            )
            st.success("✅ Cảm ơn bạn đã đánh giá! Nhật ký chat đã được cập nhật.")
        else:
            st.warning("⚠️ Không tìm thấy nhật ký chat để cập nhật phản hồi.")
