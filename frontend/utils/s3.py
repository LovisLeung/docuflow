import boto3
import streamlit as st
from botocore.exceptions import ClientError


@st.cache_resource
def get_s3_client():
    """Initialize and return an S3 client."""
    return boto3.client("s3")


def get_bucket_name_by_prefix(prefix="DocuDocs"):
    """Dynamically get the S3 bucket name using the given prefix."""
    s3 = get_s3_client()
    try:
        response = s3.list_buckets()  # list all buckets
        for bucket in response.get("Buckets", []):
            bucket_name = bucket.get("Name", "")
            # Fix: S3 bucket names are always lowercase, so we should compare case-insensitively
            if prefix.lower() in bucket_name.lower():
                return bucket_name
        return None
    except ClientError as e:
        st.error(f"Failed to get bucket name: {e}")
        return None


def upload_file_to_s3(file_object, object_name):
    """Upload a file to the specified S3 bucket."""
    bucket_name = get_bucket_name_by_prefix()
    if not bucket_name:
        st.error("Could not find S3 bucket. Please check your AWS connection.")
        return False

    s3 = get_s3_client()
    try:
        s3.upload_fileobj(
            file_object, bucket_name, object_name
        )  # upload the file object to S3
        return True
    except ClientError as e:
        st.error(f"Failed to upload file to S3: {e}")
        return False


def delete_file_from_s3(object_key):
    """Delete a file from the S3 bucket."""
    bucket_name = get_bucket_name_by_prefix()
    if not bucket_name:
        return False

    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        st.error(f"Failed to delete file from S3: {e}")
        return False
