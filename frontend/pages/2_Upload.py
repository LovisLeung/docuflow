import sys
import os
import streamlit as st
import uuid

# Ensure the utils module is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import auth, s3

st.set_page_config(page_title="Upload Document - Docuflow")

# 1. Require Login
auth.require_login()

st.title("Upload Document")
st.markdown(
    "Upload your documents to Docuflow for AI-powered metadata extraction and management."
)

# 2. File Upload Section
uploaded_file = st.file_uploader("Choose a pdf file", type="pdf")

if uploaded_file:
    # display file details
    st.write(f"Filename: {uploaded_file.name}")

    # Upload button
    if st.button("Upload to Cloud", type="primary"):
        with st.spinner("Uploading file to S3..."):
            # Generate a unique file ID for storage
            file_uuid = str(uuid.uuid4())
            original_filename = uploaded_file.name
            # build S# Key as <uuid>_<original_filename>
            s3_key = f"uploads/{file_uuid}_{original_filename}"

            # execute upload
            if s3.upload_file_to_s3(uploaded_file, s3_key):  # if upload successful
                st.success("File uploaded successfully!")
                st.info(f"File {s3_key}. Processing started...")
                st.markdown("Go to **Dashboard** to check the status.")
            else:
                st.error("File upload failed. Please try again.")
