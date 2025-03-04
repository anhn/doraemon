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

MONGO_URI = st.secrets["mongo"]["uri"]  # Load MongoDB URI from secrets
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]


st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Admin page for the UTT Tuyen sinh 👋")
# File uploader
uploaded_file = st.file_uploader("Upload an Excel file with FAQ data", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Read the Excel file
    df = pd.read_excel(uploaded_file)
    
    # Ensure required columns are present
    required_columns = {"Question", "Answer"}
    if not required_columns.issubset(df.columns):
        st.error(f"The uploaded file must contain the following columns: {required_columns}")
    else:
        # Convert DataFrame to list of dictionaries
        faq_data = df.to_dict(orient="records")
        
        # Insert data into MongoDB
        if faq_data:
            faq_collection.insert_many(faq_data)
            st.success(f"Successfully added {len(faq_data)} FAQs to the database.")
        else:
            st.warning("The uploaded file is empty or has no valid data.")

# Display existing FAQ entries
st.subheader("Existing FAQs")
faqs = list(faq_collection.find({}, {"_id": 0}))
if faqs:
    st.table(pd.DataFrame(faqs))
else:
    st.write("No FAQs found in the database.")

