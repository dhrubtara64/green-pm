"""Unit tests for GCS StorageClient — S4-06."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.storage.client import (
    GCPStorageClient,
    SignedURL,
    StorageClient,
    StubStorageClient,
)

_BUCKET = "green-pm-evidence"
_OBJECT = "photos/project-001/site_photo_abc.jpg"


# ──────────────────────────────────────────────────────────────────────────────
# SignedURL
# ──────────────────────────────────────────────────────────────────────────────

class TestSignedURL:
    def test_not_expired_when_future(self):
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        s = SignedURL(url="https://example.com/obj", expires_at=expires, object_path=_OBJECT)
        assert s.is_expired is False

    def test_expired_when_past(self):
        expires = datetime.now(timezone.utc) - timedelta(seconds=1)
        s = SignedURL(url="https://example.com/obj", expires_at=expires, object_path=_OBJECT)
        assert s.is_expired is True

    def test_is_valid_when_url_and_not_expired(self):
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        s = SignedURL(url="https://example.com/obj", expires_at=expires, object_path=_OBJECT)
        assert s.is_valid is True

    def test_not_valid_when_empty_url(self):
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        s = SignedURL(url="", expires_at=expires, object_path=_OBJECT)
        assert s.is_valid is False

    def test_frozen_dataclass(self):
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        s = SignedURL(url="https://example.com", expires_at=expires, object_path=_OBJECT)
        with pytest.raises((AttributeError, TypeError)):
            s.url = "https://other.com"  # type: ignore[misc]


# ──────────────────────────────────────────────────────────────────────────────
# StubStorageClient
# ──────────────────────────────────────────────────────────────────────────────

class TestStubStorageClient:
    def test_upload_url_returns_signed_url(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        assert isinstance(result, SignedURL)

    def test_upload_url_contains_bucket(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        assert _BUCKET in result.url

    def test_upload_url_contains_object_path(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        assert _OBJECT in result.url

    def test_upload_url_not_expired(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        assert not result.is_expired

    def test_upload_url_expires_after_custom_minutes(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT, expiry_minutes=30)
        remaining = result.expires_at - datetime.now(timezone.utc)
        assert remaining.total_seconds() > 1700  # ~28+ minutes remaining

    def test_download_url_returns_signed_url(self):
        client = StubStorageClient()
        result = client.generate_download_url(_BUCKET, _OBJECT)
        assert isinstance(result, SignedURL)

    def test_download_url_different_from_upload_url(self):
        client = StubStorageClient()
        upload = client.generate_upload_url(_BUCKET, _OBJECT)
        download = client.generate_download_url(_BUCKET, _OBJECT)
        assert upload.url != download.url

    def test_object_path_preserved(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        assert result.object_path == _OBJECT

    def test_default_expiry_is_15_minutes(self):
        client = StubStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        remaining = result.expires_at - datetime.now(timezone.utc)
        assert 800 < remaining.total_seconds() < 910


# ──────────────────────────────────────────────────────────────────────────────
# GCPStorageClient — graceful degradation
# ──────────────────────────────────────────────────────────────────────────────

class TestGCPStorageClient:
    def test_import_error_returns_empty_url(self):
        client = GCPStorageClient()
        result = client.generate_upload_url(_BUCKET, _OBJECT)
        assert isinstance(result, SignedURL)

    def test_satisfies_protocol(self):
        client = StubStorageClient()
        assert isinstance(client, StorageClient)
