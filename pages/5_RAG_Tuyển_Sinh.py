import streamlit as st
import os
import glob
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from docx import Document
import re

# Print the current working directory
current_directory = os.getcwd()
st.write(f"📂 **Current Working Directory:** `{current_directory}`")

# Load SBERT model for Vietnamese-specific text processing
sbert_model = SentenceTransformer("distiluse-base-multilingual-cased-v1")  # Optimized for Vietnamese

# Load OpenAI API key
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

# Function to extract meaningful Vietnamese keywords related to student admissions
def extract_keywords(query, top_k=5):
    words = query.split()
    if len(words) <= top_k:
        return words  # If query is short, return all words

    # Compute embeddings for each word
    word_embeddings = sbert_model.encode(words, convert_to_tensor=True).cpu().numpy()
    
    # Find the most meaningful words (by similarity ranking)
    query_embedding = sbert_model.encode([query], convert_to_tensor=True).cpu().numpy()
    similarities = np.dot(word_embeddings, query_embedding.T).flatten()
    
    # Get the top-k most relevant words
    keyword_indices = np.argsort(similarities)[-top_k:]
    keywords = [words[i] for i in keyword_indices]
    
    return keywords

# Function to search documents by keywords and extract multiple contexts (300 tokens per match, max 3000 tokens)
def search_and_extract_context(query, max_total_tokens=3000, tokens_per_match=300):
    keywords = extract_keywords(query, top_k=5)  # Extract meaningful keywords
    total_context = []
    total_tokens = 0

    for doc in documents:
        content = doc["content"].split()
        matches = [i for i, word in enumerate(content) if any(q in word.lower() for q in keywords)]

        for idx in matches:
            if total_tokens >= max_total_tokens:
                break  # Stop if we reach the 3000-token limit

            start_idx = max(0, idx - tokens_per_match // 2)
            end_idx = min(len(content), idx + tokens_per_match // 2)
            extracted_text = " ".join(content[start_idx:end_idx])

            total_context.append(f"📄 **{doc['title']}**: {extracted_text}")
            total_tokens += len(extracted_text.split())

    return "\n\n".join(total_context) if total_context else "No relevant keyword match found."

# Function to generate a response using GPT-4o with the retrieved context
def generate_gpt4o_response(question, context):
    prompt = (
        f"User asked: {question}\n\n"
        f"Based on the following extracted content from relevant documents, provide a helpful and concise response:\n\n"
        f"{context}\n\n"
        f"Ensure that the response is relevant and cost-efficient."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a cost-efficient AI assistant that answers questions based on retrieved documents."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # Reduce cost by limiting token usage
            temperature=0.2  # Keep responses factual and precise
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Streamlit UI
st.title("📚 Tư vấn tuyển sinh với RAG - Multi-Location Keyword Context")

# Display chat history
for chat in st.session_state.get("chat_history", []):
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["bot"])

# User input
user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    # Retrieve all relevant keyword locations and extract context
    context = search_and_extract_context(user_input)

    # Generate response with GPT-4o
    generated_answer = generate_gpt4o_response(user_input, context)

    # Display response
    with st.chat_message("assistant"):
        st.success("📖 **Nguồn dữ liệu từ nhiều vị trí:**")
        st.write(context)
        st.success("💡 **Câu trả lời:**")
        st.write(generated_answer)

    # Save chat to history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append(
        {"user": user_input, "bot": generated_answer}
    )

    # Store response in session state
    st.session_state["generated_answer"] = generated_answer
