import streamlit as st
import os
import glob
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from docx import Document

# Print the current working directory
current_directory = os.getcwd()
st.write(f"📂 **Current Working Directory:** `{current_directory}`")

# Load SBERT model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

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

# Function to split text into overlapping chunks (512 tokens each)
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
            chunked_titles.extend([os.path.basename(file)] * len(chunks))  

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

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "retrieved_context" not in st.session_state:
    st.session_state["retrieved_context"] = None

if "generated_answer" not in st.session_state:
    st.session_state["generated_answer"] = None

# Function to retrieve the best matching document chunk using both semantic & keyword search
def retrieve_best_chunk(query):
    if not faiss_index or not chunked_texts:
        return None, "No documents found."

    # 1️⃣ **Semantic Search (FAISS)**
    query_embedding = sbert_model.encode([query], convert_to_tensor=True).cpu().numpy()
    _, best_match_idxs = faiss_index.search(query_embedding, 3)  # Get top 3 chunks

    best_chunk_candidates = [chunked_texts[idx] for idx in best_match_idxs[0]]
    best_doc_title = chunked_titles[best_match_idxs[0][0]]

    # Find full document that contains this chunk
    best_doc = next((doc for doc in documents if doc["title"] == best_doc_title), None)

    if not best_doc:
        return None, "No relevant document found."

    # 2️⃣ **Keyword Search inside the best document**
    keyword_context = extract_relevant_text(best_doc["content"], query, max_tokens=500)

    st.session_state["retrieved_context"] = keyword_context
    return best_doc, keyword_context

# Function to extract 500 tokens around the best keyword match
def extract_relevant_text(full_text, query, max_tokens=500):
    words = full_text.split()
    query_words = query.lower().split()

    # Find keyword position
    match_positions = [i for i, word in enumerate(words) if any(q in word.lower() for q in query_words)]

    if not match_positions:
        return "No exact keyword match found. Returning semantic match."

    # Use the first found keyword position
    center_idx = match_positions[0]
    
    # Extract 500 tokens around it
    start_idx = max(0, center_idx - (max_tokens // 2))
    end_idx = min(len(words), center_idx + (max_tokens // 2))

    extracted_text = " ".join(words[start_idx:end_idx])
    return extracted_text

# Function to generate a response using GPT-4o with the retrieved context
def generate_gpt4o_response(question, context):
    prompt = (
        f"User asked: {question}\n\n"
        f"Based on the following extracted content from a relevant document, provide a helpful and concise response:\n\n"
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
st.title("📚 Tư vấn tuyển sinh với RAG - Hybrid Keyword + Semantic Search")

# Display chat history
for chat in st.session_state["chat_history"]:
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["bot"])

# User input
user_input = st.chat_input("Ask a question about the loaded documents...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    # Retrieve the most relevant chunk
    best_doc, context = retrieve_best_chunk(user_input)

    # If no documents found
    if not best_doc:
        with st.chat_message("assistant"):
            st.error("❌ No relevant documents found. Please add `.docx` files to the current folder.")
    else:
        # Generate response with GPT-4o
        generated_answer = generate_gpt4o_response(user_input, context)

        # Display response
        with st.chat_message("assistant"):
            st.success(f"📖 Retrieved Context (From **{best_doc['title']}**):")
            st.write(context)
            st.success("💡 **Generated Answer:**")
            st.write(generated_answer)

        # Save chat to history
        st.session_state["chat_history"].append(
            {"user": user_input, "bot": generated_answer}
        )

        # St
