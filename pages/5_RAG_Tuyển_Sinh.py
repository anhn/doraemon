import streamlit as st
import os
import glob
from openai import OpenAI
from pymongo import MongoClient
from docx import Document
from sentence_transformers import SentenceTransformer, util
import numpy as np

# Print the current working directory
current_directory = os.getcwd()

# Load SBERT model for embeddings
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load OpenAI API Key
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]

# Function to extract text from .docx files
def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"Error reading {docx_path}: {str(e)}"

# Load all .docx files from the current directory
@st.cache_data
def load_documents():
    docx_files = glob.glob(os.path.join(current_directory, "*.docx"))
    documents = []
    
    for file in docx_files:
        doc_text = extract_text_from_docx(file)
        if doc_text:
            documents.append({"title": os.path.basename(file), "content": doc_text})

    return documents

documents = load_documents()

# Load FAQ Data
def load_faq_data():
    return list(faq_collection.find({}, {"_id": 0, "Question": 1, "Answer": 1}))

faq_data = load_faq_data()

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Function to find the best FAQ matches using SBERT
def find_best_faq_matches(user_query, top_k=3):
    # Encode the user query using the SBERT model
    query_embedding = sbert_model.encode([user_query], convert_to_tensor=True)
    
    # Get the embeddings for FAQ questions
    faq_embeddings = sbert_model.encode([faq["Question"] for faq in faq_data], convert_to_tensor=True)
    
    # Calculate cosine similarities between the user query and each FAQ
    similarities = util.cos_sim(query_embedding, faq_embeddings)[0]
    
    # Get the top_k most similar FAQ questions
    top_k_indices = similarities.argsort()[-top_k:][::-1]
    
    best_matches = [faq_data[idx] for idx in top_k_indices]
    return best_matches

# Function to combine all document text as context
def combine_all_document_texts():
    # Combine all document texts into a single string as context
    combined_context = "\n\n".join([doc["content"] for doc in documents])
    return combined_context

# Function to generate a response using GPT with combined FAQ + document context
def generate_gpt_response(question, context):
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên thông tin sau đây, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện. "
        f"Dẫn nguồn từ nội dung có sẵn nếu cần.\n\n"
        f"Ngữ cảnh từ tài liệu:\n{context}"
    )
    try:
        # Send the request to OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích, chỉ dựa trên nội dung đã cung cấp."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        
        # Extract the response and the token usage
        generated_answer = response.choices[0].message.content.strip()
        
        # Get token usage details
        token_usage = response['usage']
        input_tokens = token_usage['prompt_tokens']
        output_tokens = token_usage['completion_tokens']
        total_tokens = input_tokens + output_tokens
        
        # Log the token usage
        st.write(f"Tokens used: Input = {input_tokens}, Output = {output_tokens}, Total = {total_tokens}")
        
        return generated_answer, input_tokens, output_tokens, total_tokens
        
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

    # Retrieve FAQ-based responses
    best_faq_matches = find_best_faq_matches(user_input)

    faq_context = "\n\n".join(
        [f"Q: {match['Question']}\nA: {match['Answer']}" for match in best_faq_matches]
    ) if best_faq_matches else ""

    if faq_context:
        final_context = faq_context
    else:
        # Use all document text as context if no good FAQ match is found
        all_documents_context = combine_all_document_texts()
        final_context = all_documents_context

    # Generate response with GPT
    generated_answer, input_tokens, output_tokens, total_tokens = generate_gpt_response(user_input, final_context)
    
    # Display the response
    with st.chat_message("assistant"):
        st.success("💡 **Câu trả lời:**")
        st.write(generated_answer)

    # Display the number of tokens used
    st.write(f"Tokens used: Input = {input_tokens}, Output = {output_tokens}, Total = {total_tokens}")

    # Append conversation to session history
    st.session_state["chat_history"].append({"user": user_input, "bot": generated_answer})
