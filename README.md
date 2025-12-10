# DocuFlow

**Turn your "dead" PDFs into "living" knowledge.**

DocuFlow is an intelligent document management system powered by **AWS Serverless** and **Generative AI (Claude 3)**. It automatically ingests, analyzes, tags, and categorizes your academic papers and technical documents.

## Key Features

*   **Smart Ingestion**: Drag & drop PDF upload.
*   **AI Analysis**: Automatically extracts summaries, semantic tags, and categories using **Amazon Bedrock (Claude 3 Haiku)**.
*   **Cost-Optimized**: Uses a "Semantic Extraction" strategy to minimize token usage (Head/Tail + Keyword Targeting).
*   **Serverless Architecture**: Built on AWS Lambda, S3, and DynamoDB for zero-maintenance scalability.

## Architecture

1.  **Upload**: User uploads PDF to S3 Bucket (`/inbox`).
2.  **Trigger**: S3 event triggers a Python Lambda function.
3.  **Process**:
    *   Lambda extracts text (Smart Head/Tail + Semantic Chunking).
    *   Calls **Claude 3 Haiku** to analyze content.
4.  **Store**: Metadata saved to **DynamoDB**; File moved to structured S3 paths.
5.  **UI**: (Coming Soon) Streamlit frontend for search and visualization.

## Deployment (Dev Guide)

### Prerequisites
*   AWS CLI configured
*   Node.js & NPM (for CDK)
*   Python 3.12+
*   Docker (optional, for Lambda bundling)

### Setup

1.  **Clone & Install Dependencies**
    ```bash
    git clone https://github.com/LovisLeung/docuflow.git
    cd docuflow
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    ```

2.  **Deploy Infrastructure**
    ```bash
    cdk bootstrap  # Run once per region
    cdk deploy
    ```

## License

MIT
