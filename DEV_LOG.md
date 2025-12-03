# Development Log

## 2025-11-30: Initial Project Setup - Infrastructure & Ingestion
**Phase Target:** Phase 1 Backend Completion
- Set up AWS CDK development environment (Python + Node.js).
- Designed core infrastructure:
  - S3 Buckets for file ingestion and processed storage.
  - Lambda functions for file processing and AI integration.
  - DynamoDB table for metadata storage.
- Deployed initial infrastructure using AWS CDK.
- Implemented S3 event triggers to invoke Lambda on file upload (event-driven architecture).

**Design Decisions:**
- Chose serverless architecture for scalability and cost-efficiency.
- Reason for Streamlit frontend: Rapid prototyping and ease of deployment. May transition to React in future phases.
- DynamoDB Schema:
  - PartitionKey: `file_id` (UUIDv4) for global uniqueness. Ensures even distribution of read/write load.
  - GSI: `category-index` for efficient category-based navigation. Optimizes sidebar navigation performance (avoids full scans).
  - Projection: All. Sacrificed storage cost for query flexibility.

**Next Steps:**
- Implement PDF processing pipeline in Lambda (pypdf2 + custom extraction logic).
- Integrate Amazon Bedrock for AI analysis.
- Design prompts for Claude 3 Haiku to extract summaries and tags.

## 2025-12-03: PDF Processing & AI Integration
**Phase Target:** Complete Document Processing Pipeline
- Developed PDF text extraction logic using `pypdf` (migrated from PyPDF2 for better maintenance).
- Implemented intelligent chunking of large documents for subsequent AI processing.
  - **Strategy:** "Head-4 Tail-5" (Pages, not lines).
  - **Fallback:** If chunked text doesn't contain sufficient info, extend chunk scope to Head-20 Tail-20 (Deep scan).
- Integrated Amazon Bedrock with Claude 3 Haiku for document analysis.
- Created prompt templates for summary and tag extraction.
- Implemented DynamoDB storage logic for processed metadata.

**Technical Fixes & Infrastructure:**
- **IAM Permissions:** Updated CDK stack to explicitly grant `bedrock:InvokeModel` permission to the Lambda execution role.
- **Client Initialization:** Fixed a bug where `boto3.client("bedrock")` was used for inference instead of `boto3.client("bedrock-runtime")`.
- **Environment Variables:** Decoupled `TABLE_NAME` and `BUCKET_NAME` using Lambda environment variables for better IaC practices.

**Key Algorithms:**
- **Head-4 Tail-5 Page Extraction:**
  - Reasoning: 99% of academic/professional documents have critical info in intro/conclusion.
  - Implementation: Extract first 4 pages and last 5 pages. This captures essential information while saving ~80% of token usage compared to full-text processing.
- **Reference Cleaning:**
  - Regex patterns to identify and remove common reference sections (e.g., "References", "Bibliography").
  - Reduces token noise and prevents AI from hallucinating based on citation titles.

**Next Steps:**
- Implement the "File Routing" logic (Move file from `/inbox` to `/processed/...` in S3).
- Increase Lambda timeout (currently 30s) to handle "Deep Scan" scenarios.
- Test end-to-end pipeline with sample PDFs.
