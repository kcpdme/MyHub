from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from app.config import settings


def media_storage_backend() -> str:
    return (settings.media_storage_backend or "local").strip().lower()


def is_r2_enabled() -> bool:
    return (
        media_storage_backend() == "r2"
        and bool(settings.media_r2_account_id.strip())
        and bool(settings.media_r2_bucket.strip())
        and bool(settings.media_r2_access_key_id.strip())
        and bool(settings.media_r2_secret_access_key.strip())
    )


@lru_cache(maxsize=1)
def _r2_client():
    endpoint = f"https://{settings.media_r2_account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.media_r2_access_key_id,
        aws_secret_access_key=settings.media_r2_secret_access_key,
        region_name="auto",
    )


def media_object_key(file_unique_id: str, file_id: str, item_id: int) -> str:
    stable = (file_unique_id or "").strip() or (file_id or "").strip() or f"item_{item_id}"
    return f"telegram/{stable}"


def get_media_from_r2(object_key: str) -> tuple[bytes, str] | None:
    if not is_r2_enabled():
        return None

    try:
        resp = _r2_client().get_object(Bucket=settings.media_r2_bucket, Key=object_key)
        body = resp.get("Body")
        if not body:
            return None
        data = body.read()
        content_type = (resp.get("ContentType") or "application/octet-stream").strip()
        return data, content_type
    except ClientError as exc:
        code = str((exc.response or {}).get("Error", {}).get("Code", ""))
        if code in {"NoSuchKey", "404", "NotFound"}:
            return None
        print(f"[media] R2 get failed for key={object_key}: {exc}")
        return None
    except Exception as exc:
        print(f"[media] R2 get error for key={object_key}: {exc}")
        return None


def put_media_to_r2(object_key: str, content: bytes, content_type: str) -> None:
    if not is_r2_enabled():
        return

    try:
        _r2_client().put_object(
            Bucket=settings.media_r2_bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )
    except Exception as exc:
        print(f"[media] R2 put failed for key={object_key}: {exc}")