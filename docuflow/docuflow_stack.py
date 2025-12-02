from aws_cdk import (
    Stack,  # resource stack
    RemovalPolicy,
    aws_s3 as s3,  # S3 bucket
    aws_dynamodb as dynamodb,  # DynamoDB table
    aws_lambda as _lambda,  # Lambda function, distinguished from python lambda keyword by underscore
    Duration,  # time duration
    aws_s3_notifications as s3n,  # S3 notifications (to trigger Lambda on S3 events)
)
from constructs import Construct  # base construct class


class DocuflowStack(Stack):  # define stack for Docuflow application

    def __init__(
        self, scope: Construct, construct_id: str, **kwargs
    ) -> None:  # initialize stack for resources, eg S3, DynamoDB.
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 Bucket
        docs_bucket = s3.Bucket(  # new instance of S3 Bucket
            self,
            "DocuDocs",  # S3 bucket name for document storage
            versioned=True,  # Enable versioning for documents, helps in tracking changes
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # 2. DynamoDB Table
        table = dynamodb.Table(
            self,
            "DocuMetaTable",
            partition_key=dynamodb.Attribute(  # aws will use hash value of this attribute to partition data
                name="file_id",
                type=dynamodb.AttributeType.STRING,  # every document has a unique file_id
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # for development purposes. In production, consider using RETAIN.
        )

        # Add GSI(Global Secondary Index) for Category Search （全局二级索引�?        # This index allows querying documents based on their category attribute.
        table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(
                name="category",
                type=dynamodb.AttributeType.STRING,  # search documents by category eg: CS, NLP...
            ),
            projection_type=dynamodb.ProjectionType.ALL,  # include all attributes in the index when querying
        )

        # 3. Define Lambda Function
        process_doc_lambda = _lambda.Function(
            self,
            "ProcessDocFunction",  # logical name for the Lambda function
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="process_doc.handler",  # file is process_doc.py, function is handler(process_doc.handler)
            code=_lambda.Code.from_asset(
                "lambda"
            ),  # tell cdk that lambda code is in lambda/ directory
            timeout=Duration.seconds(
                30
            ),  # timeout after 30 seconds, prevent long-running executions
            environment={
                "TABLE_NAME": table.table_name,  # pass DynamoDB table name to Lambda environment variable
                "BUCKET_NAME": docs_bucket.bucket_name,
            },
        )

        # Bind S3 bucket event to Lambda function
        docs_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(
                process_doc_lambda
            ),  # trigger Lambda on new object creation
            s3.NotificationKeyFilter(suffix=".pdf"),  # only for .pdf files
        )

        # Grant permissions to Lambda function
        docs_bucket.grant_read_write(
            process_doc_lambda
        )  # grant copy and delete permissions on S3 bucket(imitate move operation which is not natively supported in S3)
        table.grant_read_write_data(
            process_doc_lambda
        )  # grant read and write permissions on DynamoDB table
