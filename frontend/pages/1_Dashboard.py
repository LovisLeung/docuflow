import sys
import os

# Ensure the utils module is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from utils import auth
from utils import db
import pandas as pd


# DynamoDB Table Schema Example:
# [
#     {
#         "file_id": "123",
#         "original_file_name": "paper.pdf",
#         "status": "AUTO_TAGGED",
#         "ai_summary": {"tags": ["#AI"], "summary": "..."}
#     },
#     ...
# ]


def get_tags(row):
    """Helper function to extract tags from ai_summary field."""
    ai_summary = row.get("ai_summary", {})
    tags = ai_summary.get("tags", [])
    return (
        ", ".join(tags) if tags else "N/A"
    )  # return comma-separated tags or N/A eg: #AI, #ML


# 1. Page Configuration(must be at the top)
st.set_page_config(page_title="Dashboard - Docuflow")

# 2. Require Login
auth.require_login()

# 3. fetch data from DynamoDB
files = db.get_all_files()
if not files:
    st.info("No files found in the database.")
    st.stop()  # Stop execution if no files found

# Convert to DataFrame for better display
df = pd.DataFrame(files)  # convert list of dicts to DataFrame
st.title("Document Dashboard")

# 1. Clean up DataFrame for display
df["Tags"] = df.apply(get_tags, axis=1)  # extract tags for each row

# 2. select and rename columns
display_df = df[["original_file_name", "status", "Tags", "upload_timestamp"]].copy()
display_df.columns = ["File Name", "Status", "Tags", "Uploaded At"]

# Convert 'Uploaded At' to datetime objects to match column config
display_df["Uploaded At"] = pd.to_datetime(display_df["Uploaded At"])

# 3. use data_editor to display the advanced table
st.data_editor(
    display_df,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=[
                "UPLOADED",
                "PROCESSING",
                "AUTO_TAGGED",
                "MANUAL_TAGGED",
                "ERROR",
            ],
            width="medium",
            required=True,
        ),
        "Uploaded At": st.column_config.DatetimeColumn(
            "Uploaded At",
            format="YYYY-MM-DD HH:mm:ss",
        ),
        "Tags": st.column_config.TextColumn(
            "Tags",
            width="large",
        ),
    },
    hide_index=True,
    use_container_width=True,
    disabled=True,  # make the table read-only temporarily
)

st.caption(f"Total Documents: {len(files)}")
