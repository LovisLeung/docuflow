import sys
import os
import streamlit as st
import pandas as pd
import time


# Ensure the utils module is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import auth, db, embedding

# Page Configuration(must be at the top)
st.set_page_config(page_title="Review - Docuflow")
# Require Login
# auth.require_login()

st.title("Review and Edit Document Metadata")
st.markdown(
    "Review the AI-extracted metadata for your documents. You can edit tags and summaries as needed."
)

# 1. Display
# fetch data from DynamoDB
files = db.get_all_files()
if not files:
    st.info("No files found in the database.")
    st.stop()  # Stop execution if no files found

# clean up data
for file in files:
    details = db.get_file_details(file)
    file.update(details)

# Convert to DataFrame for better display
df = pd.DataFrame(files)  # convert list of dicts to DataFrame
# extract tags and summaries for each row
target_columns = ["file_name", "tags", "summary", "category", "status"]
st.dataframe(df[target_columns])

st.divider()

# 2. Select
# prepare a dictionary
file_options = {f["file_id"]: f["file_name"] for f in files}

# create a dropdown to select a file
selected_file_id = st.selectbox(
    "Select a file to review/edit metadata:",
    options=list(file_options.keys()),  # select by file_id
    format_func=lambda x: file_options[x],  # display file name instead of file_id
)

# 3. Edit
selected_file = next((f for f in files if f["file_id"] == selected_file_id), None)

if selected_file:
    with st.form(key="edit_form"):
        # create input fields and pre-fill with existing data
        new_category = st.text_input(
            "Category", value=selected_file.get("category", "")
        )
        current_tags = ", ".join(selected_file.get("tags", []))
        new_tags = st.text_input("Tags (comma-separated)", value=current_tags)
        new_summary = st.text_area("Summary", value=selected_file.get("summary", ""))

        col1, col2 = st.columns([1, 1])
        with col1:
            # Submit button
            submit_button = st.form_submit_button(label="Submit Changes")
        with col2:
            delete_button = st.form_submit_button(label="Delete File", type="primary")

        if submit_button:
            # Save logic here
            updated_tags = [tag.strip() for tag in new_tags.split(",") if tag.strip()]
            # build the update dictionary(ai_summary)
            updated_ai_summary = {
                "tags": updated_tags,
                "summary": new_summary,
                "category": new_category,
            }

            # --- Generate Embedding ---
            with st.spinner("Generating new embeddings..."):
                # Combine text for embedding: Title + Summary + Tags
                # This provides a rich context for semantic search
                text_to_embed = f"{selected_file.get('file_name', '')}\n{new_summary}\n{' '.join(updated_tags)}"
                new_embedding = embedding.generate_embedding(text_to_embed)

            if new_embedding:
                # call db function to update the item
                # Update ai_summary, status, and embedding all at once
                updates = {
                    "ai_summary": updated_ai_summary,
                    "status": "REVIEWED",
                    "embedding": new_embedding,
                }
                success = db.update_file_metadata(selected_file_id, updates)

                if success:
                    st.success("Metadata updated & Embeddings generated successfully!")
                    # delay to show the success message before refreshing

                    time.sleep(1)
                    st.rerun()  # refresh the page to show updated data
                else:
                    st.error("Failed to update metadata.")
            else:
                st.error("Failed to generate embeddings. Changes not saved.")

        if delete_button:
            if db.delete_file(selected_file_id):
                st.success("File deleted successfully.")
                # delay to show the success message before refreshing

                time.sleep(1)
                st.rerun()  # refresh the page to reflect deletion
            else:
                st.error("Failed to delete file.")
