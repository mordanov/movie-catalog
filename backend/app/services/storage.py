import httpx
from aiobotocore.session import get_session
from botocore.config import Config

from app.config import get_settings


async def upload_poster(url: str, filename: str) -> str:
    """Download poster from URL and upload to S3-compatible storage. Returns public URL."""
    async with httpx.AsyncClient() as http:
        resp = await http.get(url, follow_redirects=True)
        resp.raise_for_status()

    s = get_settings()
    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if s.s3_force_path_style else "virtual"},
    )
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=s.s3_endpoint,
        region_name=s.s3_region,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        config=cfg,
    ) as client:
        try:
            await client.create_bucket(Bucket=s.s3_bucket)
        except client.exceptions.BucketAlreadyOwnedByYou:
            pass
        except Exception:
            pass  # bucket may already exist or creation not needed (Hetzner pre-configured)

        await client.put_object(
            Bucket=s.s3_bucket,
            Key=f"{s.s3_key_prefix}{filename}",
            Body=resp.content,
            ContentType="image/jpeg",
            ACL="public-read",
        )

    if s.s3_public_url:
        return f"{s.s3_public_url.rstrip('/')}/{filename}"
    return f"/{s.s3_bucket}/{filename}"
