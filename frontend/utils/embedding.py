import boto3
import json
import streamlit as st


@st.cache_resource
def get_bedrock_runtime():
    """Initialize and return a Bedrock runtime client."""
    return boto3.client("bedrock-runtime", region_name="us-east-1")


def generate_embedding(text):
    """Generate embedding for the given text using Bedrock embedding model."""
    client = get_bedrock_runtime()
    # Titan Embeddings v2 model ID
    model_id = "amazon.titan-embed-text-v2:0"  # search in Bedrock - Model catalog - Titan Text Embedding v2
    # build the request body
    body = json.dumps(
        {
            "inputText": text,  # text to be embedded
            "dimensions": 1024,  # embedding dimensions
            "normalize": True,  # normalize the embedding vector to calculate cosine similarity further
        }
    )

    try:
        response = client.invoke_model(
            modelId=model_id,
            body=body,
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response.get("body").read())
        embedding = response_body.get("embedding", [])
        return embedding