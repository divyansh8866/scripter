import boto3
from botocore.exceptions import ClientError

def list_buckets():
    """
    List and print all S3 bucket names in your AWS account.
    (No parameters required—this will always be detected by the GUI.)
    """
    try:
        s3 = boto3.client("s3")
        response = s3.list_buckets()
        buckets = response.get("Buckets", [])
        if not buckets:
            print("No S3 buckets found.")
        else:
            print("S3 Buckets:")
            for b in buckets:
                print(f"  - {b['Name']}")
        return [b["Name"] for b in buckets]
    except ClientError as e:
        print(f"Error listing buckets: {e}")
        raise