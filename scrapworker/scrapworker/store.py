import json
import logging

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


def build_s3_client(rustfs_cfg: dict) -> boto3.client:
    return boto3.client(
        "s3",
        endpoint_url=rustfs_cfg["endpoint"],
        aws_access_key_id=rustfs_cfg["access_key"],
        aws_secret_access_key=rustfs_cfg["secret_key"],
        config=Config(s3={"addressing_style": "path"} if rustfs_cfg.get("path_style") else {}),
    )


def write_raw(rustfs_cfg: dict, job: dict, rows: list[dict]) -> None:
    """Write accumulated rows to RustFS at the path specified in the job payload."""
    s3 = build_s3_client(rustfs_cfg)

    bucket = rustfs_cfg["bucket"]
    key = job["s3_path"]

    body = json.dumps(rows).encode("utf-8")
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")

    logger.info("Wrote %d rows to s3://%s/%s", len(rows), bucket, key)
