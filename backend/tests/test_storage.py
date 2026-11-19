import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.storage import (
    LocalStorageProvider,
    S3StorageProvider,
    StorageProvider,
    get_storage,
)


def test_local_storage_provider_upload_bytes():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = LocalStorageProvider(base_dir=Path(tmpdir))
        key = "products/test_item.webp"
        data = b"RIFF\x00\x00\x00\x00WEBPVP8 "

        url = provider.upload_file(data, key, content_type="image/webp")
        assert url == "/media/products/test_item.webp"
        assert provider.file_exists(key) is True
        assert (Path(tmpdir) / key).read_bytes() == data

        deleted = provider.delete_file(key)
        assert deleted is True
        assert provider.file_exists(key) is False


def test_local_storage_provider_upload_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = LocalStorageProvider(base_dir=Path(tmpdir))
        src_file = Path(tmpdir) / "source.txt"
        src_file.write_text("sample content", encoding="utf-8")

        key = "docs/sample.txt"
        url = provider.upload_file(src_file, key)
        assert url == "/media/docs/sample.txt"
        assert provider.file_exists(key) is True


def test_s3_storage_provider_url_generation_standard():
    mock_boto = MagicMock()
    with patch.dict("sys.modules", {"boto3": mock_boto, "botocore": MagicMock(), "botocore.config": MagicMock()}):
        with patch("app.services.storage.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                STORAGE_BACKEND="s3",
                AWS_REGION="ap-south-1",
                AWS_S3_BUCKET_NAME="my-store-bucket",
                AWS_S3_CUSTOM_DOMAIN=None,
            )
            provider = S3StorageProvider()
            url = provider.get_url("products/silk_dhoti_men.webp")
            assert url == "https://my-store-bucket.s3.ap-south-1.amazonaws.com/products/silk_dhoti_men.webp"


def test_s3_storage_provider_url_generation_cloudfront():
    mock_boto = MagicMock()
    with patch.dict("sys.modules", {"boto3": mock_boto, "botocore": MagicMock(), "botocore.config": MagicMock()}):
        with patch("app.services.storage.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                STORAGE_BACKEND="s3",
                AWS_REGION="ap-south-1",
                AWS_S3_BUCKET_NAME="my-store-bucket",
                AWS_S3_CUSTOM_DOMAIN="d123456abcdef.cloudfront.net",
            )
            provider = S3StorageProvider()
            url = provider.get_url("/catalog/products.json")
            assert url == "https://d123456abcdef.cloudfront.net/catalog/products.json"


def test_get_storage_factory():
    with patch("app.services.storage._storage_singleton", None):
        storage = get_storage()
        assert isinstance(storage, LocalStorageProvider)
