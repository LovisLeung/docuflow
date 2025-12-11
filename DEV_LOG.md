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

## 2025-12-10: Frontend Initialization & Dashboard Implementation
**Phase Target:** Phase 2 Frontend Development (Streamlit)
- Initialized Streamlit project structure:
  - `frontend/Home.py`: Main entry point and login page.
  - `frontend/pages/`: Directory for multi-page navigation.
  - `frontend/utils/`: Utility modules for authentication and database connection.
- Implemented Authentication Logic (`utils/auth.py`):
  - Created session-based login system (simulated for now).
  - Developed `require_login` decorator with in-place login form for seamless user experience.
- Implemented Database Connection (`utils/db.py`):
  - Used `boto3` to connect to DynamoDB.
  - **Dynamic Table Discovery:** Implemented logic to automatically find the DynamoDB table by prefix (`DocuMetaTable`), eliminating the need for hardcoded table names in frontend code.
  - Added `ClientError` handling for robust AWS interactions.
- Developed Dashboard Page (`pages/1_Dashboard.py`):
  - Fetches metadata from DynamoDB.
  - **ETL Pipeline:** Implemented in-memory ETL using Pandas to clean and format raw JSON data.
  - **UI/UX:** Used `st.data_editor` for a modern, Excel-like table view with formatted dates and status dropdowns.
- **Refactoring:**
  - Fixed Python path issues (`sys.path.append`) to ensure `utils` module is accessible from sub-pages.
  - Optimized code structure by using `st.stop()` to reduce indentation levels (Guard Clause pattern).

**Next Steps:**
- Implement `2_Upload.py` to handle file uploads to S3.
- Connect the upload action to the backend Lambda trigger.

**Pending Issues / Technical Debt:**
- **S3 File Overwrite Risk:** Currently, if two files with the same name are uploaded, S3 will overwrite the content, but DynamoDB will generate two different `file_id`s pointing to the same `s3_key`.
  - **Planned Fix:** In the Frontend Upload phase (`2_Upload.py`), generate the UUID *before* uploading to S3, and use the UUID as the S3 object key (e.g., `uploads/{uuid}.pdf` or `uploads/{uuid}_{filename}.pdf`). This ensures S3 keys are immutable and unique.

- **AI Tag/Category Explosion:** Without constraints, the AI might generate semantically identical but syntactically different tags (e.g., "AI" vs "Artificial Intelligence", "CS" vs "Computer Science"). This leads to a fragmented knowledge base ("Tag Hell").
  - **Potential Solutions:**
    1. **Pre-defined Taxonomy:** Force AI to choose from a fixed list of categories (e.g., arXiv categories).
    2. **Semantic Deduplication:** Use embeddings to merge similar tags in the background.
    3. **Frontend Autocomplete:** When users manually edit tags, suggest existing tags from the database to encourage consistency.
