import io
import json

import httpx
from minio import Minio
from minio.error import S3Error

from app.config import get_settings

_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        s = get_settings()
        _client = Minio(
            s.minio_endpoint,
            access_key=s.minio_root_user,
            secret_key=s.minio_root_password,
            secure=False,
        )
        try:
            if not _client.bucket_exists(s.minio_bucket):
                _client.make_bucket(s.minio_bucket)
            policy = json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{s.minio_bucket}/*"],
                        }
                    ],
                }
            )
            _client.set_bucket_policy(s.minio_bucket, policy)
        except S3Error:
            pass
    return _client


async def upload_poster(url: str, filename: str) -> str:
    """Download poster from URL and upload to MinIO. Returns internal URL."""
    async with httpx.AsyncClient() as http:
        resp = await http.get(url, follow_redirects=True)
        resp.raise_for_status()

    s = get_settings()
    client = _get_client()
    data = resp.content
    client.put_object(
        s.minio_bucket,
        filename,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg",
    )
    return f"/{s.minio_bucket}/{filename}"
