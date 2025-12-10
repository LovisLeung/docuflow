import json
import urllib.parse  # For URL decoding
import boto3  # AWS SDK for Python
import os
import re  # Regular expressions
import datetime
import uuid  # For generating unique file IDs
from pypdf import PdfReader  # PDF processing library

#  init clients
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name="us-east-1"
)  # Bedrock is only available in us-east-1 as of now

# environment variables： Captured table and bucket names from CDK stack deployment
TABLE_NAME = os.environ.get("TABLE_NAME")
BUCKET_NAME = os.environ.get("BUCKET_NAME")


def download_file_from_s3_to_tmp(bucket_name, key):
    """
    Download a file from S3 to the /tmp directory in Lambda.
    :param bucket_name: The name of the S3 bucket
    :param key: The S3 object key (file name)
    :return: The local file path where the file is downloaded
    """
    local_path = (
        f"/tmp/{os.path.basename(key)}"  # /tmp is the only writable directory in Lambda
    )
    s3_client.download_file(
        bucket_name, key, local_path
    )  # Download file from S3 to /tmp
    return local_path


def clean_reference(text):
    """
    Regex to find common reference patterns and truncate text after them.
    """
    match = re.search(
        r"\n\s*(?:References?|Bibliography|Citations?|Appendix(?:es)?)\s*(?::|\n)",
        text,
        re.IGNORECASE,
    )  # Match common reference section headers
    if match:
        print("Found reference section, truncating text...")
        return text[: match.start()]
    return text


def extract_sections_by_keywords(text):
    """
    Try to extract specific high-value sections (Abstract, Intro, Conclusion) based on keywords.
    Returns the combined extracted text if successful, or None if not enough content found.
    """
    # Define the sections we are interested in
    # Format: (SectionName, MaxLength)
    targets = [
        (r"(?:Abstract|Executive Summary)", 1500),
        (r"(?:Introduction|Background)", 2000),
        (r"(?:Conclusion|Future Work|Summary)", 1500),
    ]

    extracted_parts = []

    for pattern, max_len in targets:
        # Find the section header, requiring it to be on a new line or followed by a colon
        match = re.search(rf"\n\s*{pattern}\s*(?::|\n)", text, re.IGNORECASE)
        if match:
            start_idx = match.end()
            # Extract content after the header
            content = text[start_idx : start_idx + max_len]
            extracted_parts.append(f"--- {pattern} ---\n{content}...\n")

    # If too little content was extracted (e.g., no headers found), return None to fallback
    if not extracted_parts:
        return None

    return "\n".join(extracted_parts)


def extract_text_smartly(pdf_path, head=4, tail=5):
    """
    Extract text from a PDF file, removing the first few pages and the last few pages.
    :param pdf_path: Path to the PDF file
    :param head: Number of pages to skip from the start
    :param tail: Number of pages to skip from the end
    :return: Cleaned text from the PDF
    """
    try:
        reader = PdfReader(pdf_path)  # Read the PDF file
        total_pages = len(reader.pages)  # Get total number of pages
        text_content = []

        if total_pages <= head + tail:
            pages_to_read = range(total_pages)  # If not enough pages, read all
        else:
            head_pages = range(0, head)  # Pages to skip from the start
            tail_pages = range(
                total_pages - tail, total_pages
            )  # Pages to skip from the end
            pages_to_read = sorted(
                list(set(list(head_pages) + list(tail_pages)))
            )  # Combine and sort the pages to read
        print(f"Total pages: {total_pages}, Reading pages: {list(pages_to_read)}")

        for i in pages_to_read:
            try:
                page_text = reader.pages[
                    i
                ].extract_text()  # Extract text from each page
                if page_text:
                    text_content.append(page_text)  # Append non-empty text
            except Exception:
                continue  # Skip pages that cannot be read

        full_text = "\n".join(text_content)  # Join all text into a single string
        cleaned_text = clean_reference(full_text)  # Clean up references
        return (
            cleaned_text.strip()
        )  # Return cleaned text, removing leading/trailing whitespace
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""  # Return empty string on error


def ask_bedrock_model(text):
    """
    Send the extracted text to an Amazon Bedrock model for processing.
    :param text: The text extracted from the PDF
    :return: The response from the Bedrock model
    """

    # prompt construction
    prompt = f"""
    You are an expert research librarian. Analyze the following academic paper text (which is truncated).

    <text>
    {text}
    </text>

    Your task:
    1. Summarize the core contribution (1-2 sentences).
    2. Extract 3-5 semantic tags (e.g., #Transformer, #MedicalImage).
    3. Categorize it into a hierarchy like "CS/AI/NLP".

    CRITICAL INSTRUCTION:
    If the text is too fragmented or missing the conclusion/summary to the point where you cannot form a valid analysis, 
    you MUST output a JSON with "status": "INSUFFICIENT_DATA". DO NOT HALLUCINATE.
    
    Otherwise, output valid JSON:
    {{
        "status": "SUCCESS",
        "summary": "...",
        "tags": ["#Tag1", "#Tag2"],
        "category": "Domain/SubDomain"
    }}
    Output ONLY JSON.
    """

    # request body containing model parameters, token limits, and the constructed prompt
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    try:
        # invoke bedrock model
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0", body=body
        )
        response_body = json.loads(response.get("body").read())  # Parse response body
        ai_reply = response_body["content"][0][
            "text"
        ]  # Extract model's reply text, structure may vary by model

        # Try to extract JSON from the model's reply
        try:
            json_str = ai_reply[ai_reply.find("{") : ai_reply.rfind("}") + 1]
            return json.loads(json_str)
        except Exception as e:
            print(
                f"Error parsing JSON from model response: {ai_reply}, Error: {str(e)}"
            )
            return {"status": "ERROR", "message": "Failed to parse model response"}
    except Exception as e:
        print(f"Error invoking Bedrock model: {str(e)}")
        return {"status": "ERROR", "message": {str(e)}}


def save_metadata_to_DDB(file_id, original_file_name, s3_key, ai_result):
    table = dynamodb.Table(TABLE_NAME)
    ai_status = ai_result.get("status", "ERROR")
    if ai_status == "SUCCESS":
        final_status = "AUTO_TAGGED"
    else:
        final_status = "NEEDS_REVIEW"
    print(f"AI processing status: {ai_status} -> final status: {final_status}")
    item = {
        "file_id": file_id,
        "original_file_name": original_file_name,
        "s3_key": s3_key,
        "upload_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),  # ISO 8601 format
        "status": final_status,  # AUTO_TAGGED, NEEDS_REVIEW, etc.
        "ai_summary": ai_result,  # Store full AI result for reference (json dict concluding status, summary, tags, category)
        "user_notes": "",  # Placeholder for user notes
        "is_verified": False,  # Placeholder for verification status
    }

    try:
        table.put_item(Item=item)
        print(f"Metadata saved to DynamoDB for file_id: {file_id}")
    except Exception as e:
        print(f"Error saving metadata to DynamoDB: {str(e)}")
        raise e


def handler(event, context):
    """
    This is the entry point for the Lambda function. AWS will call this function when a file is uploaded to S3, passing information about the file in the 'event' parameter.
    :param event: The event data from S3, it is a dictionary containing details about the S3 object that triggered the Lambda function
    :param context: The runtime information of the Lambda function
    :return: A dictionary with status code and message
    """
    print(
        "Received event: " + json.dumps(event, indent=2)
    )  # Log the received event for debugging. indent=2 makes it pretty-printed

    # 1. 从 event 里解析出是谁触发了我
    # (S3 发来的消息里包含 bucket 名字和 file key)
    try:
        record = event["Records"][
            0
        ]  # event的结构：{"Records": [ { "s3": { "bucket": { "name": "my-bucket" }, "object": { "key": "my-file.txt" } } } ] }
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(
            record["s3"]["object"]["key"], encoding="utf-8"
        )  # unquote_plus 用于解码 URL 编码的字符串, 比如把 %20 转换为空格。将s3 object key 解码成正常文件名

        print(
            f"Processing file: s3://{bucket}/{key}"
        )  # Log the bucket and key being processed

        # 2. download the file from S3 to /tmp
        local_file_path = download_file_from_s3_to_tmp(bucket, key)

        # 3. Round 1: Standard scan (Head4 + Tail5)
        print("Starting Round 1: Standard scan (Head4 + Tail5)")
        text = extract_text_smartly(local_file_path, head=4, tail=5)

        # 3.1 Try Semantic Extraction (Keyword-based)
        # If we can find Abstract/Intro/Conclusion, use that instead of the full text to save tokens.
        semantic_text = extract_sections_by_keywords(text)
        if semantic_text and len(semantic_text) > 600:
            print("Semantic extraction successful! Using optimized text.")
            text = semantic_text
        else:
            print("Semantic extraction failed or too short. Using full Head+Tail text.")

        ai_result = None  # placeholder for AI result
        if not text or len(text) < 100:  # too little text extracted
            print("Insufficient text extracted in Round 1.")
            ai_result = {
                "status": "INSUFFICIENT_DATA"
            }  # dict indicating insufficient data
        else:
            ai_result = ask_bedrock_model(text)
            if ai_result.get("status") == "INSUFFICIENT_DATA":
                print("Round 1 result: INSUFFICIENT_DATA")

        # 4. Round 2: Deep scan (Smart retry)
        if ai_result.get("status") == "INSUFFICIENT_DATA":
            print("Starting Round 2: Deep scan (Head20 + Tail20)")
            text_deep = extract_text_smartly(local_file_path, head=20, tail=20)
            if text_deep and len(text_deep) > len(text) + 500:
                ai_result = ask_bedrock_model(text_deep)
                ai_result["retry_performed"] = True  # mark that we did a retry
            else:
                print("Deep scan did not yield significantly more text.")

        # 5. Save metadata to DynamoDB
        # Generate a unique file_id using UUIDv4. This ensures stability even if the file is renamed or moved.
        file_id = str(uuid.uuid4())
        save_metadata_to_DDB(
            file_id=file_id,
            original_file_name=os.path.basename(key),
            s3_key=key,  # S3 object key
            ai_result=ai_result,
        )

        return {
            "statusCode": 200,
            "body": json.dumps("Processing complete."),
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise e
