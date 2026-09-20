import io

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
    return f"http://{s.minio_endpoint}/{s.minio_bucket}/{filename}"
