import json
import urllib.parse  # For URL decoding
import boto3  # AWS SDK for Python


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
            f"New task received for file upload."
        )  # Log that a new file upload task has been received
        print(f"Bucket: {bucket}")
        print(f"File: {key}")

        return {
            "statusCode": 200,
            "body": json.dumps(f"Successfully processed {key}"),
        }  # return a dictionary containing status code and message

    except Exception as e:
        print(f"Error: {str(e)}")
        raise e
