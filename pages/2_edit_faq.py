import streamlit as st
import pandas as pd
import os
from pymongo import MongoClient

st.set_page_config(layout="wide") 

# Load MongoDB URI from secrets
MONGO_URI = st.secrets["mongo"]["uri"]  
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"

# Connect to MongoDB
client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]

st.set_page_config(
    page_title="Admin Page for UTT Tuyển Sinh",
    page_icon="👋",
)

st.write("# Admin Page for UTT Tuyển Sinh 👋")

# Load existing FAQ data from MongoDB
faqs = list(faq_collection.find({}, {"_id": 0}))
faq_df = pd.DataFrame(faqs)

if faq_df.empty:
    st.warning("No FAQ data found in the database.")
else:
    st.subheader("Editable FAQ Data")
    edited_df = st.data_editor(faq_df, num_rows="dynamic")

    # Button to save changes to MongoDB
    if st.button("Save Changes to Database"):
        if not edited_df.empty:
            faq_collection.delete_many({})  # Clear existing data
            faq_collection.insert_many(edited_df.to_dict(orient="records"))
            st.success("Database updated successfully!")
        else:
            st.warning("No data to save!")
