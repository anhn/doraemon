import streamlit as st
import pandas as pd
import os
from pymongo import MongoClient

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
uploaded_file = st.file_uploader("Upload an Excel file with FAQ data", type=["csv"])

if uploaded_file is not None:
    # Read the CSV file
    df = pd.read_csv(uploaded_file, encoding="utf-8",  delimiter=";")
    
    # Ensure required columns are present
    required_columns = {"Question", "Answer", "Type"}
    if not required_columns.issubset(df.columns):
        st.error(f"The uploaded file must contain the following columns: {required_columns}")
    else:
        # Filter only Type 1 entries
        df_filtered = df[df["Type"] == 1]
        
        # Show the first 10 rows
        st.subheader("Preview of Uploaded Data (First 10 Rows)")
        st.dataframe(df_filtered.head(10))
        
        # Convert DataFrame to list of dictionaries
        faq_data = df_filtered.drop(columns=["Type"]).to_dict(orient="records")
        
        # Button to save data to the database
        if st.button("Save to Database"):
            if faq_data:
                faq_collection.insert_many(faq_data)
                st.success(f"Successfully added {len(faq_data)} FAQs of Type 1 to the database.")
            else:
                st.warning("No valid Type 1 FAQs found in the uploaded file.")

# Display existing FAQ entries
st.subheader("Existing FAQs")
faqs = list(faq_collection.find({}, {"_id": 0}))
if faqs:
    st.table(pd.DataFrame(faqs))
else:
    st.write("No FAQs found in the database.")
