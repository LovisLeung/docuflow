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


# get DynamoDB table instance
def get_all_files():
    """fetch all files record from DynamoDB table."""
    dynamodb = get_dynamodb_resource()

    # 1. get dynamic table name
    table_name = get_table_name_by_prefix()

    if not table_name:
        st.error("Couldn't find the DynamoDB table. Please check your AWS connection.")
        return []

    # 2. scan the table
    table = dynamodb.Table(table_name)
    try:
        response = table.scan()  # scan the entire table to get all items
        items = response.get("Items", [])
        return items
    except ClientError as e:
        st.error(
            f"Failed to fetch items from DynamoDB: {e.response['Error']['Message']}"
        )
        return []
