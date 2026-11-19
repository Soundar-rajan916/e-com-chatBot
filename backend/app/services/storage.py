import abc
import logging
import mimetypes
from pathlib import Path
from typing import Any

from app.config import get_settings

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")

logger = logging.getLogger(__name__)


class StorageProvider(abc.ABC):
    """Abstract interface for storing and retrieving product assets."""

    @abc.abstractmethod
    def upload_file(
        self,
        file_path_or_bytes: Path | bytes | bytearray,
        key: str,
        content_type: str | None = None,
        cache_control: str = "public, max-age=31536000, immutable",
    ) -> str:
        """Uploads a file or bytes to storage under `key` and returns its public URL."""
        pass

    @abc.abstractmethod
    def get_url(self, key: str) -> str:
        """Returns the public CDN or direct URL for a given storage key."""
        pass

    @abc.abstractmethod
    def delete_file(self, key: str) -> bool:
        """Deletes an object with key from storage."""
        pass

    @abc.abstractmethod
    def file_exists(self, key: str) -> bool:
        """Checks if a file exists in storage."""
        pass


class S3StorageProvider(StorageProvider):
    """Amazon S3 implementation of StorageProvider with CloudFront CDN support."""

    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        settings = get_settings()
        self.bucket = settings.AWS_S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        self.custom_domain = settings.AWS_S3_CUSTOM_DOMAIN

        session_kwargs: dict[str, Any] = {"region_name": self.region}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            config=Config(signature_version="s3v4"),
            **session_kwargs,
        )
        logger.info(
            "S3StorageProvider initialized for bucket='%s', region='%s', domain='%s'",
            self.bucket,
            self.region,
            self.custom_domain or "standard-s3",
        )

    def upload_file(
        self,
        file_path_or_bytes: Path | bytes | bytearray,
        key: str,
        content_type: str | None = None,
        cache_control: str = "public, max-age=31536000, immutable",
    ) -> str:
        clean_key = key.lstrip("/")
        if not content_type:
            content_type, _ = mimetypes.guess_type(clean_key)
            content_type = content_type or "application/octet-stream"

        extra_args: dict[str, str] = {
            "ContentType": content_type,
            "CacheControl": cache_control,
        }

        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=clean_key,
                Body=file_path_or_bytes,
                **extra_args,
            )
        else:
            self.s3_client.upload_file(
                str(file_path_or_bytes),
                self.bucket,
                clean_key,
                ExtraArgs=extra_args,
            )

        return self.get_url(clean_key)

    def get_url(self, key: str) -> str:
        clean_key = key.lstrip("/")
        if self.custom_domain:
            domain = self.custom_domain.rstrip("/")
            if not domain.startswith("http"):
                domain = f"https://{domain}"
            return f"{domain}/{clean_key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{clean_key}"

    def delete_file(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=clean_key)
            return True
        except Exception as e:
            logger.warning("Failed to delete s3://%s/%s: %s", self.bucket, clean_key, e)
            return False

    def file_exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        clean_key = key.lstrip("/")
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=clean_key)
            return True
        except ClientError:
            return False


class LocalStorageProvider(StorageProvider):
    """Local disk storage provider for development and testing."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (Path(__file__).resolve().parent.parent.parent / "media")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info("LocalStorageProvider initialized at path='%s'", self.base_dir)

    def upload_file(
        self,
        file_path_or_bytes: Path | bytes | bytearray,
        key: str,
        content_type: str | None = None,
        cache_control: str = "public, max-age=31536000, immutable",
    ) -> str:
        clean_key = key.lstrip("/")
        target_path = self.base_dir / clean_key
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            target_path.write_bytes(file_path_or_bytes)
        else:
            import shutil

            shutil.copy2(str(file_path_or_bytes), str(target_path))

        return self.get_url(clean_key)

    def get_url(self, key: str) -> str:
        clean_key = key.lstrip("/")
        return f"/media/{clean_key}"

    def delete_file(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        target_path = self.base_dir / clean_key
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def file_exists(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        return (self.base_dir / clean_key).exists()


_storage_singleton: StorageProvider | None = None


def get_storage() -> StorageProvider:
    """Returns the configured storage provider based on STORAGE_BACKEND setting."""
    global _storage_singleton
    if _storage_singleton is not None:
        return _storage_singleton

    settings = get_settings()
    if settings.STORAGE_BACKEND.lower() == "s3":
        _storage_singleton = S3StorageProvider()
    else:
        _storage_singleton = LocalStorageProvider()

    return _storage_singleton
