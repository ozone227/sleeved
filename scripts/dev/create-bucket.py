#!/usr/bin/env python3
"""Create the local `sleeved-collection` bucket configured like prod (see scripts/setup-bucket.sh):
versioning, public-read policy, CORS.

Idempotent. Reads S3_ENDPOINT / S3_BUCKET / AWS_* from the environment, falling
back to the local-cluster defaults from .env.example.
"""
import json
import os
import time

import boto3
from botocore.exceptions import ClientError, ConnectionError as BotoConnectionError

endpoint = os.environ.get("S3_ENDPOINT", "http://sleeved-storage.localhost:8080")
bucket = os.environ.get("S3_BUCKET", "sleeved-collection")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "dev"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "dev"),
    region_name="us-east-1",
)

for attempt in range(60):  # Traefik may take a moment to come up and pick up the route
    try:
        s3.head_bucket(Bucket=bucket)
        break
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
            break
        raise
    except BotoConnectionError:  # includes the LB closing the connection before Traefik is up
        time.sleep(2)
else:
    raise SystemExit(f"Could not reach {endpoint}")

s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
s3.put_bucket_cors(Bucket=bucket, CORSConfiguration={"CORSRules": [{
    "AllowedHeaders": ["*"], "AllowedMethods": ["GET", "HEAD"], "AllowedOrigins": ["*"],
}]})
s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "PublicReadGetObject",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": f"arn:aws:s3:::{bucket}/*",
    }],
}))
print(f"bucket ready: {endpoint}/{bucket}")

# Seed the same scaffold setup-bucket.sh uploads, only if absent so re-running
# `make dev-up` never clobbers cards you've uploaded.
def put_if_absent(key: str, doc: dict) -> None:
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
            raise
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(doc, indent=2).encode(),
                      ContentType="application/json")
        print(f"seeded {key}")


put_if_absent("cyberpunk-tcg/inventory.json", {
    "game": "cyberpunk-tcg",
    "displayName": "Cyberpunk TCG",
    "lastUpdated": "",
    "structure": {
        "types": ["Legend", "Unit", "Program", "Gear"],
        "colors": ["Red", "Green", "Blue", "Yellow"],
        "coloredTypes": ["Unit", "Program", "Gear"],
    },
    "cards": [],
})
put_if_absent("games.json", {"games": [{
    "id": "cyberpunk-tcg",
    "displayName": "Cyberpunk TCG",
    "inventoryPath": "cyberpunk-tcg/inventory.json",
}]})
