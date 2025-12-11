# This file contains connection utility for the database
import boto3
import os
import streamlit as st
from boto3.dynamodb.conditions import Key  # for querying
from botocore.exceptions import ClientError


# initiate DynamoDB resource
@st.cache_resource
def get_dynamodb_resource():
    return boto3.resource("dynamodb")


def get_table_name_by_prefix(prefix="DocuMetaTable"):
    """Dynamically get the DB table name using the given prefix."""
    try:
        client = boto3.client("dynamodb")
        paginator = client.get_paginator("list_tables")  # paginator for listing tables

        # iterate through pages of table names
        for page in paginator.paginate():
            for table_name in page.get("TableNames", []):
                if prefix in table_name:
                    return table_name
        return None
    except Exception as e:
        st.error(f"Failed to get table name: {e}")
        return None


def get_table():
    """Get DynamoDB table instance by dynamic name."""
    dynamodb = get_dynamodb_resource()
    table_name = get_table_name_by_prefix()
    if not table_name:
        st.error("Couldn't find the DynamoDB table. Please check your AWS connection.")
        return None
    return dynamodb.Table(table_name)


# get DynamoDB table instance
def get_all_files():
    """fetch all files record from DynamoDB table."""
    table = get_table()
    try:
        response = table.scan()  # scan the entire table to get all items
        items = response.get("Items", [])
        return items
    except ClientError as e:
        st.error(
            f"Failed to fetch items from DynamoDB: {e.response['Error']['Message']}"
        )
        return []


def update_file_metadata(file_id, updates):
    """Update metadata of a file in DynamoDB table."""
    table = get_table()

    # Build the update expression
    update_parts = []
    attr_names = {}
    attr_values = {}

    for key, value in updates.items():
        k_placeholder = f"#{key}"  # eg: #status
        v_placeholder = f":{key}"  # eg: :status
        update_parts.append(f"{k_placeholder} = {v_placeholder}")

        attr_names[k_placeholder] = key
        attr_values[v_placeholder] = value

        # concatenate SET expressions
        update_expression = "SET " + ", ".join(update_parts)

    try:
        table.update_item(
            Key={"file_id": file_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
        )
        return True
    except ClientError as e:
        st.error(f"Failed to update item in DynamoDB: {e.response['Error']['Message']}")
        return False


def get_file_by_id(file_id):
    """Fetch a single file record by file_id from DynamoDB table."""
    table = get_table()
    try:
        response = table.get_item(Key={"file_id": file_id})
        item = response.get("Item", None)
        return item
    except ClientError as e:
        st.error(
            f"Failed to fetch item from DynamoDB: {e.response['Error']['Message']}"
        )
        return None


def get_file_details(item):
    """Fetch file details including cleaned filename and AI summary."""
    # Default value
    file_name = "N/A"

    try:
        original_file_name = item.get("original_file_name", "N/A")
        # Split only on the first underscore to preserve underscores in the actual filename
        file_name = (
            original_file_name.split("_", 1)[1]
            if "_" in original_file_name
            else original_file_name
        )

        ai_summary = item.get("ai_summary", {})
        return {
            "file_name": file_name,
            "tags": ai_summary.get("tags", []),
            "summary": ai_summary.get("summary", ""),
            "category": ai_summary.get("category", "N/A"),
        }

    except Exception as e:
        st.error(f"Failed to get file details: {e}")
        return {"file_name": file_name, "tags": [], "summary": "", "category": "N/A"}


from utils.s3 import delete_file_from_s3


def delete_file(file_id):
    """Delete a file record from DynamoDB table and S3."""
    # 1. Get the file info first to find the S3 key
    item = get_file_by_id(file_id)
    if item:
        s3_key = item.get("s3_key")
        if s3_key:
            # 2. Delete from S3
            delete_file_from_s3(s3_key)
        else:
            st.warning(f"No s3_key found for file {file_id}, skipping S3 deletion.")

    # 3. Delete from DynamoDB
    table = get_table()
    try:
        table.delete_item(Key={"file_id": file_id})
        return True
    except ClientError as e:
        st.error(
            f"Failed to delete item from DynamoDB: {e.response['Error']['Message']}"
        )
        return False
