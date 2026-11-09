"""Adapter: AWS S3 -> BaseStorage port."""

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import AppSettings
from app.core.exceptions import StorageError
from app.domains.interfaces.storage import BaseStorage


class S3Storage(BaseStorage):
    def __init__(self, settings: AppSettings) -> None:
        aws = settings.aws
        if not aws.s3_bucket_name:
            raise StorageError("AWS_S3_BUCKET_NAME is empty. Add it to your .env.")

        self._bucket = aws.s3_bucket_name
        self._presign_expiry = aws.presign_expiry

        session = boto3.session.Session(
            aws_access_key_id=aws.access_key_id or None,
            aws_secret_access_key=(
                aws.secret_access_key.get_secret_value()
                if aws.secret_access_key
                else None
            ),
            region_name=aws.region,
        )
        # s3v4 -> presigned URLs work for any region
        self._client = session.client("s3", config=BotoConfig(signature_version="s3v4"))

    def put(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        self._client.put_object(
            Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )
        return f"s3://{self._bucket}/{key}"

    def get(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise StorageError(
                    f"Object not found: s3://{self._bucket}/{key}"
                ) from e
            raise

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_url(self, key: str, expires_in: int | None = None) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in or self._presign_expiry,
        )
