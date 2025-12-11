import boto3
import json
import streamlit as st
from decimal import Decimal


@st.cache_resource
def get_bedrock_runtime():
    return boto3.client("bedrock-runtime", region_name="us-east-1")


def generate_embedding(text):
    client = get_bedrock_runtime()
    model_id = "amazon.titan-embed-text-v2:0"
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=body,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(response.get("body").read())
        embedding = response_body.get("embedding")
        # Convert float to Decimal for DynamoDB compatibility
        if embedding:
            return [Decimal(str(x)) for x in embedding]
        return None
    except Exception as e:
        st.error(f"Failed to generate embedding: {e}")
        return None
