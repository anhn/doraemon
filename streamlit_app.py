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
METAINFO_COLLECTION = "metainfo"
TS24_VIECLAM_COLLECTION = "ts24_vieclam"
TS24_CHITIEU_COLLECTION = "ts24_chitieu"
TS24_ADMISSION_COLLECTION = "ts24_admission"
TS24_CHITIEU_TRUNGCAP_COLLECTION = "ts24_chitieu_trungcap"


# Load OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-4-turbo"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
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

# Database Collections
collections_info = {
    "faqtuyensinh": {
        "name": "FAQ Tuyển Sinh",
        "description": "Câu hỏi thường gặp về tuyển sinh và nhập học.",
        "search_field": "Question",
        "response_field": "Answer"
    },
    "metainfo": {
        "name": "Thông Tin Chung về Trường",
        "description": "Thông tin chung về trường, liên hệ, địa điểm, các khoa đào tạo.",
        "search_field": "Question",
        "response_field": "Answer"
    },
    "ts24_vieclam": {
        "name": "Thống kê Việc Làm Sinh Viên Tốt nghiệp 2024",
        "description": "Thống kê sinh viên tốt nghiệp 2024, số lượng có việc làm theo ngành học.",
        "search_field": "Question",
        "response_field": "Answer"
    }
}

def load_context():
    collections = {
    "ts24_chitieu": "Chỉ tiêu tuyển sinh 2024",
    "ts24_admission": "Phương thức xét tuyển 2024",
    "ts24_chitieu_trungcap": "Chỉ tiêu tuyển sinh trung cấp 2024"
    }
    context_parts = []
    for collection_name, description in collections.items():
        collection = db[collection_name]
        docs = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB _id field  
        collection_text = f"{description}:\n"
        for doc in docs:
            doc_text = ", ".join([f"{key}: {value}" for key, value in doc.items()])
            collection_text += f"- {doc_text}\n"
        context_parts.append(collection_text)
    return "\n".join(context_parts)

context_string = load_context()
def load_data():
    """Loads data from MongoDB and converts to searchable format."""
    all_data = []
    
    for collection_name, info in collections_info.items():
        collection = db[collection_name]
        docs = list(collection.find({}, {"_id": 0}))  # Exclude MongoDB _id field
        
        for doc in docs:
            if isinstance(info["search_field"], list):
                searchable_texts = [doc.get(field, "") for field in info["search_field"] if field in doc]
            else:
                searchable_texts = [doc.get(info["search_field"], "")]

            if isinstance(info["response_field"], list):
                answer_text = "\n".join(str(doc.get(k, "")) for k in info["response_field"] if k in doc)
            else:
                answer_text = str(doc.get(info["response_field"], ""))
                
            # Convert into a single searchable text entry
            searchable_text = f"{info['description']}: {', '.join(searchable_texts)}"
            
            if searchable_text.strip() and answer_text.strip():
                all_data.append({
                    "text": searchable_text,
                    "answer": answer_text,
                    "source": collection_name
                })
    
    return all_data

# Load and process data
data = load_data()
texts = [entry["text"] for entry in data]
answers = [entry["answer"] for entry in data]

# Generate embeddings
if texts:
    text_embeddings = sbert_model.encode(texts, convert_to_tensor=True).cpu().numpy()
    
    # Create FAISS index
    dimension = text_embeddings.shape[1]
    faiss_index = faiss.IndexFlatL2(dimension)
    faiss_index.add(text_embeddings)
else:
    faiss_index = None
    
# --- FUNCTION FOR SEMANTIC SEARCH ---
def search_database(query, threshold=0.7):
    """Finds the best-matching answer using FAISS and SBERT."""
    if not faiss_index:
        return None   
    query_embedding = sbert_model.encode([query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idx = faiss_index.search(query_embedding, 1)
    print(best_match_idx[0][0])
    best_match = data[best_match_idx[0][0]]
    print(best_match)
    similarity = util.cos_sim(query_embedding, text_embeddings[best_match_idx[0][0]]).item()
    if similarity >= threshold:
        return best_match["answer"]
    return None

# Function to find best match using SBERT
def find_best_match(user_query):
    query_embedding = sbert_model.encode([user_query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idx = faiss_index.search(query_embedding, 1)
    best_match = load_data()[best_match_idx[0][0]]
    # Compute similarity
    best_match_embedding = question_embeddings[best_match_idx[0][0]]
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

def format_gpt4_response(question, answer, context):
    prompt = (
        f"Dựa vào câu trả lời {answer} cho câu hỏi {question}. Kiểm tra tính chính xác của câu trả lời bằng thông tin từ {context} hoặc từ Internet." 
        f"Nểu bạn thấy câu trả lời sai, đưa ra lý giải."
        f"Nếu đúng hãy cho câu trả lời ngắn gọn, dễ hiểu, và thân thiện như một tư vấn viên tuyển sinh chuyên nghiệp."
        f"Hãy giữ văn chat lịch sự, ít tính hình thức, gần gũi theo phong cách miền Bắc Việt Nam"
    )   
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Bạn là một tư vấn viên tuyển sinh chuyên nghiệp, cung cấp câu trả lời thân thiện, rõ ràng theo giọng miền Bắc Việt Nam."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Lỗi: {str(e)}"
        
# Function to save chat logs to MongoDB
def save_chat_log(user_ip, user_message, bot_response, feedback):
    """Stores chat log into MongoDB."""
    chat_entry = {
        "user_ip": user_ip,
        "timestamp": datetime.utcnow(),
        "user_message": user_message,
        "bot_response": bot_response,
        "is_good": feedback is None,
        "problem_detail": feedback or ""
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
    # Search in the selected collection
    result = search_database(user_input)
    use_gpt = False
    if result:
            response_stream = stream_text(format_gpt4_response(user_input,result,context_string))  # FAQ converted to a generator
    else:
            st.warning("⚠️ Không tìm thấy trong cơ sở dữ liệu. Đang tìm kiếm bằng AI...")
            use_gpt = True
            response_stream = format_gpt4_response(user_input,generate_gpt4_response(user_input, ""),context_string)  # Now a generator
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
    feedback=""
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
                        "user_message": st.session_state["chat_log"][-1]["user"],  # Update user question
                        "bot_response": st.session_state["chat_log"][-1]["bot"]  # Update bot response
                    }
                }
            )
            st.success("✅ Cảm ơn bạn đã đánh giá! Nhật ký chat đã được cập nhật.")
        else:
            st.warning("⚠️ Không tìm thấy nhật ký chat để cập nhật phản hồi.")
