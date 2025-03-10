import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import numpy as np
import faiss

# Load SBERT Model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"

# Connect to MongoDB
client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]

# Load FAQ Data
def load_faq_data():
    return list(faq_collection.find({}, {"_id": 0}))

# Get Latest Question ID
def get_next_question_id():
    latest_faq = faq_collection.find().sort("ID", -1).limit(1)
    latest_id = next(latest_faq, {}).get("ID", "Q000")
    next_id_num = int(latest_id[1:]) + 1
    return f"Q{next_id_num:03d}"

# Retrieve Wrong Answers from Chatlog
def load_wrong_answers():
    chat_data = list(chatlog_collection.find({"is_good": False}, {"_id": 0, "user_message": 1, "bot_response": 1, "problem_detail": 1, "timestamp": 1}))
    df = pd.DataFrame(chat_data)
    if not df.empty:
        df = df.rename(columns={"user_message": "Question", "bot_response": "Wrong Answer", "problem_detail": "Correct Answer"})
        df = df.sort_values(by="timestamp", ascending=False)  # Sort by latest time
    return df

# Check for Semantic Match in FAQ
def find_best_match(question):
    faq_data = load_faq_data()
    if not faq_data:
        return None, 0

    faq_questions = [item["Question"] for item in faq_data]
    faq_embeddings = sbert_model.encode(faq_questions, convert_to_tensor=True).cpu().numpy()

    faiss_index = faiss.IndexFlatL2(faq_embeddings.shape[1])
    faiss_index.add(faq_embeddings)

    query_embedding = sbert_model.encode([question], convert_to_tensor=True).cpu().numpy()
    _, best_match_idx = faiss_index.search(query_embedding, 1)

    best_match = faq_data[best_match_idx[0][0]]
    similarity = util.cos_sim(query_embedding, sbert_model.encode(best_match["Question"], convert_to_tensor=True)).item()
    
    return best_match, similarity

# Streamlit UI
st.title("📌 FAQ Management - Correct & Add Questions")

if st.button("Retrieve All"):
    wrong_answers_df = load_wrong_answers()
    if wrong_answers_df.empty:
        st.warning("No incorrect answers found.")
    else:
        st.write("### Editable Questions & Answers")
        edited_df = st.data_editor(wrong_answers_df, num_rows="dynamic")

        if st.button("Add to Database"):
            added_count = 0
            for _, row in edited_df.iterrows():
                question = row["Question"]
                corrected_answer = row["Correct Answer"]

                best_match, similarity = find_best_match(question)
                if best_match and similarity > 0.85:
                    # If question exists, update the answer
                    faq_collection.update_one({"Question": best_match["Question"]}, {"$set": {"Answer": corrected_answer}})
                else:
                    # Add as a new entry
                    new_entry = {
                        "QuestionID": get_next_question_id(),
                        "Question": question,
                        "Answer": corrected_answer
                    }
                    faq_collection.insert_one(new_entry)
                    added_count += 1

            st.success(f"✅ {added_count} new questions added! Existing ones were updated.")

  
