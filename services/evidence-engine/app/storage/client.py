"""GCS Signed URL storage client — S4-06.

Protocol + GCP implementation (lazy import) + Stub for tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class SignedURL:
    url: str
    expires_at: datetime
    object_path: str

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return bool(self.url) and not self.is_expired


@runtime_checkable
class StorageClient(Protocol):
    def generate_upload_url(
        self, bucket: str, object_path: str, *, expiry_minutes: int = 15
    ) -> SignedURL: ...

    def generate_download_url(
        self, bucket: str, object_path: str, *, expiry_minutes: int = 15
    ) -> SignedURL: ...


class GCPStorageClient:
    """GCS signed URL client with lazy google-cloud-storage import."""

    def __init__(self, credentials_path: str = "") -> None:
        self._credentials_path = credentials_path

    def generate_upload_url(
        self, bucket: str, object_path: str, *, expiry_minutes: int = 15
    ) -> SignedURL:
        try:
            from google.cloud import storage as gcs  # type: ignore[import]

            client = gcs.Client()
            blob = client.bucket(bucket).blob(object_path)
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiry_minutes),
                method="PUT",
                version="v4",
            )
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
            return SignedURL(url=url, expires_at=expires_at, object_path=object_path)
        except ImportError:
            return SignedURL(url="", expires_at=datetime.now(timezone.utc), object_path=object_path)
        except Exception as exc:
            return SignedURL(url="", expires_at=datetime.now(timezone.utc), object_path=object_path)

    def generate_download_url(
        self, bucket: str, object_path: str, *, expiry_minutes: int = 15
    ) -> SignedURL:
        try:
            from google.cloud import storage as gcs  # type: ignore[import]

            client = gcs.Client()
            blob = client.bucket(bucket).blob(object_path)
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiry_minutes),
                method="GET",
                version="v4",
            )
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
            return SignedURL(url=url, expires_at=expires_at, object_path=object_path)
        except ImportError:
            return SignedURL(url="", expires_at=datetime.now(timezone.utc), object_path=object_path)
        except Exception as exc:
            return SignedURL(url="", expires_at=datetime.now(timezone.utc), object_path=object_path)


class StubStorageClient:
    """Deterministic test double — returns predictable URLs with correct expiry."""

    _BASE = "https://storage.googleapis.com"

    def generate_upload_url(
        self, bucket: str, object_path: str, *, expiry_minutes: int = 15
    ) -> SignedURL:
        url = f"{self._BASE}/{bucket}/{object_path}?sig=stub-upload&method=PUT"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        return SignedURL(url=url, expires_at=expires_at, object_path=object_path)

    def generate_download_url(
        self, bucket: str, object_path: str, *, expiry_minutes: int = 15
    ) -> SignedURL:
        url = f"{self._BASE}/{bucket}/{object_path}?sig=stub-download&method=GET"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
        return SignedURL(url=url, expires_at=expires_at, object_path=object_path)
