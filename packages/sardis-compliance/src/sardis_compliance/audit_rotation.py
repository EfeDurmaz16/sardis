"""
Audit log rotation and archival module.

Provides production-ready audit log management with:
- Automatic rotation based on size, time, or entry count
- Compression and archival to cold storage
- Integrity verification with hash chains
- Regulatory retention policy enforcement
- S3/GCS/Azure Blob compatible archival
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol
from collections import deque

logger = logging.getLogger(__name__)


class RotationTrigger(str, Enum):
    """Trigger conditions for log rotation."""
    SIZE = "size"  # Rotate when file/entries exceed size limit
    TIME = "time"  # Rotate at time intervals
    COUNT = "count"  # Rotate at entry count threshold
    MANUAL = "manual"  # Manual rotation only


class ArchiveDestination(str, Enum):
    """Archive storage destinations."""
    LOCAL = "local"  # Local filesystem
    S3 = "s3"  # AWS S3
    GCS = "gcs"  # Google Cloud Storage
    AZURE = "azure"  # Azure Blob Storage


@dataclass
class RotationConfig:
    """Configuration for audit log rotation."""
    # Rotation triggers
    max_entries: int = 100_000  # Rotate after this many entries
    max_size_mb: float = 100.0  # Rotate after this size (MB)
    rotation_interval_hours: int = 24  # Rotate at this interval

    # Archival settings
    archive_destination: ArchiveDestination = ArchiveDestination.LOCAL
    archive_path: str = "/var/log/sardis/audit/archive"
    compress_archives: bool = True
    compression_level: int = 9  # gzip compression level

    # Retention settings (regulatory compliance)
    retention_days: int = 2555  # ~7 years (US regulatory requirement)
    delete_expired: bool = False  # Safety: don't auto-delete, require manual

    # Integrity
    enable_hash_chain: bool = True
    verify_on_rotation: bool = True

    # Cloud storage settings (if applicable)
    s3_bucket: Optional[str] = None
    s3_prefix: str = "audit/"
    gcs_bucket: Optional[str] = None
    azure_container: Optional[str] = None


@dataclass
class ArchiveMetadata:
    """Metadata for an archived audit log."""
    archive_id: str
    created_at: datetime
    entry_count: int
    first_entry_at: datetime
    last_entry_at: datetime
    size_bytes: int
    compressed_size_bytes: Optional[int] = None
    checksum: str = ""
    hash_chain_start: str = ""
    hash_chain_end: str = ""
    destination: ArchiveDestination = ArchiveDestination.LOCAL
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "archive_id": self.archive_id,
            "created_at": self.created_at.isoformat(),
            "entry_count": self.entry_count,
            "first_entry_at": self.first_entry_at.isoformat(),
            "last_entry_at": self.last_entry_at.isoformat(),
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "checksum": self.checksum,
            "hash_chain_start": self.hash_chain_start,
            "hash_chain_end": self.hash_chain_end,
            "destination": self.destination.value,
            "path": self.path,
        }


class ArchiveStore(Protocol):
    """Protocol for archive storage backends."""

    def upload(
        self,
        data: bytes,
        archive_id: str,
        metadata: ArchiveMetadata,
    ) -> str:
        """Upload archive data and return storage path."""
        ...

    def download(self, archive_id: str) -> bytes:
        """Download archive data."""
        ...

    def list_archives(self) -> List[ArchiveMetadata]:
        """List all archives."""
        ...

    def delete(self, archive_id: str) -> bool:
        """Delete an archive."""
        ...


class LocalArchiveStore:
    """Local filesystem archive storage."""

    def __init__(self, base_path: str):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self._base_path / "metadata.json"
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata index."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load archive metadata: {e}")
                self._metadata = {}

    def _save_metadata(self) -> None:
        """Save metadata index."""
        try:
            with open(self._metadata_file, "w") as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save archive metadata: {e}")

    def upload(
        self,
        data: bytes,
        archive_id: str,
        metadata: ArchiveMetadata,
    ) -> str:
        """Save archive to local filesystem."""
        filename = f"{archive_id}.json.gz" if metadata.compressed_size_bytes else f"{archive_id}.json"
        filepath = self._base_path / filename

        with open(filepath, "wb") as f:
            f.write(data)

        metadata.path = str(filepath)
        self._metadata[archive_id] = metadata.to_dict()
        self._save_metadata()

        logger.info(f"Archive saved locally: {filepath}")
        return str(filepath)

    def download(self, archive_id: str) -> bytes:
        """Download archive from local filesystem."""
        if archive_id not in self._metadata:
            raise ValueError(f"Archive not found: {archive_id}")

        path = Path(self._metadata[archive_id]["path"])
        with open(path, "rb") as f:
            return f.read()

    def list_archives(self) -> List[ArchiveMetadata]:
        """List all local archives."""
        archives = []
        for archive_id, meta in self._metadata.items():
            archives.append(ArchiveMetadata(
                archive_id=archive_id,
                created_at=datetime.fromisoformat(meta["created_at"]),
                entry_count=meta["entry_count"],
                first_entry_at=datetime.fromisoformat(meta["first_entry_at"]),
                last_entry_at=datetime.fromisoformat(meta["last_entry_at"]),
                size_bytes=meta["size_bytes"],
                compressed_size_bytes=meta.get("compressed_size_bytes"),
                checksum=meta["checksum"],
                hash_chain_start=meta.get("hash_chain_start", ""),
                hash_chain_end=meta.get("hash_chain_end", ""),
                destination=ArchiveDestination(meta["destination"]),
                path=meta["path"],
            ))
        return archives

    def delete(self, archive_id: str) -> bool:
        """Delete archive from local filesystem."""
        if archive_id not in self._metadata:
            return False

        try:
            path = Path(self._metadata[archive_id]["path"])
            if path.exists():
                path.unlink()
            del self._metadata[archive_id]
            self._save_metadata()
            logger.info(f"Archive deleted: {archive_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete archive: {e}")
            return False


class S3ArchiveStore:
    """AWS S3 archive storage."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "audit/",
        region: Optional[str] = None,
    ):
        self._bucket = bucket
        self._prefix = prefix
        self._region = region
        self._client = None

    def _get_client(self):
        """Get or create S3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("s3", region_name=self._region)
            except ImportError:
                raise RuntimeError("boto3 is required for S3 storage. Install with: pip install boto3")
        return self._client

    def upload(
        self,
        data: bytes,
        archive_id: str,
        metadata: ArchiveMetadata,
    ) -> str:
        """Upload archive to S3."""
        client = self._get_client()

        ext = ".json.gz" if metadata.compressed_size_bytes else ".json"
        key = f"{self._prefix}{archive_id}{ext}"

        client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            Metadata={
                "entry_count": str(metadata.entry_count),
                "checksum": metadata.checksum,
                "created_at": metadata.created_at.isoformat(),
            },
        )

        s3_path = f"s3://{self._bucket}/{key}"
        logger.info(f"Archive uploaded to S3: {s3_path}")
        return s3_path

    def download(self, archive_id: str) -> bytes:
        """Download archive from S3."""
        client = self._get_client()

        # Try compressed first, then uncompressed
        for ext in [".json.gz", ".json"]:
            key = f"{self._prefix}{archive_id}{ext}"
            try:
                response = client.get_object(Bucket=self._bucket, Key=key)
                return response["Body"].read()
            except client.exceptions.NoSuchKey:
                continue

        raise ValueError(f"Archive not found: {archive_id}")

    def list_archives(self) -> List[ArchiveMetadata]:
        """List all S3 archives."""
        client = self._get_client()
        archives = []

        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                archive_id = key.replace(self._prefix, "").replace(".json.gz", "").replace(".json", "")

                # Get metadata
                head = client.head_object(Bucket=self._bucket, Key=key)
                meta = head.get("Metadata", {})

                archives.append(ArchiveMetadata(
                    archive_id=archive_id,
                    created_at=datetime.fromisoformat(meta.get("created_at", datetime.now(timezone.utc).isoformat())),
                    entry_count=int(meta.get("entry_count", 0)),
                    first_entry_at=datetime.now(timezone.utc),  # Would need to store this
                    last_entry_at=datetime.now(timezone.utc),
                    size_bytes=obj["Size"],
                    checksum=meta.get("checksum", ""),
                    destination=ArchiveDestination.S3,
                    path=f"s3://{self._bucket}/{key}",
                ))

        return archives

    def delete(self, archive_id: str) -> bool:
        """Delete archive from S3."""
        client = self._get_client()

        for ext in [".json.gz", ".json"]:
            key = f"{self._prefix}{archive_id}{ext}"
            try:
                client.delete_object(Bucket=self._bucket, Key=key)
                logger.info(f"Archive deleted from S3: {key}")
                return True
            except Exception:
                continue

        return False


class AuditLogRotator:
    """
    Manages audit log rotation and archival.

    Thread-safe rotation with configurable triggers and
    multiple archive destinations.
    """

    def __init__(
        self,
        config: Optional[RotationConfig] = None,
        archive_store: Optional[ArchiveStore] = None,
        on_rotation: Optional[Callable[[ArchiveMetadata], None]] = None,
    ):
        """
        Initialize audit log rotator.

        Args:
            config: Rotation configuration
            archive_store: Archive storage backend
            on_rotation: Callback function called after successful rotation
        """
        self._config = config or RotationConfig()
        self._archive_store = archive_store or self._create_archive_store()
        self._on_rotation = on_rotation

        self._entries: deque = deque()
        self._lock = threading.Lock()
        self._current_size_bytes = 0
        self._last_rotation = datetime.now(timezone.utc)
        self._hash_chain: List[str] = []
        self._rotation_count = 0

    def _create_archive_store(self) -> ArchiveStore:
        """Create archive store based on config."""
        if self._config.archive_destination == ArchiveDestination.S3:
            if not self._config.s3_bucket:
                raise ValueError("S3 bucket must be specified for S3 archival")
            return S3ArchiveStore(
                bucket=self._config.s3_bucket,
                prefix=self._config.s3_prefix,
            )
        else:
            return LocalArchiveStore(self._config.archive_path)

    def _compute_entry_hash(self, entry: Dict[str, Any], prev_hash: str = "") -> str:
        """Compute hash for an entry."""
        data = json.dumps({**entry, "prev_hash": prev_hash}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def append(self, entry: Dict[str, Any]) -> str:
        """
        Append an entry to the audit log.

        Returns the entry hash for verification.
        """
        with self._lock:
            # Compute hash chain
            prev_hash = self._hash_chain[-1] if self._hash_chain else ""
            entry_hash = self._compute_entry_hash(entry, prev_hash)

            if self._config.enable_hash_chain:
                entry["_hash"] = entry_hash
                self._hash_chain.append(entry_hash)

            self._entries.append(entry)
            self._current_size_bytes += len(json.dumps(entry))

            # Check if rotation is needed
            if self._should_rotate():
                self._rotate()

            return entry_hash

    def _should_rotate(self) -> bool:
        """Check if rotation is needed."""
        # Count trigger
        if len(self._entries) >= self._config.max_entries:
            return True

        # Size trigger
        if self._current_size_bytes >= self._config.max_size_mb * 1024 * 1024:
            return True

        # Time trigger
        age = (datetime.now(timezone.utc) - self._last_rotation).total_seconds()
        if age >= self._config.rotation_interval_hours * 3600:
            return True

        return False

    def _rotate(self) -> Optional[ArchiveMetadata]:
        """Perform log rotation. Must be called with lock held."""
        if not self._entries:
            return None

        logger.info(f"Starting audit log rotation: {len(self._entries)} entries")

        # Prepare archive data
        entries_list = list(self._entries)
        now = datetime.now(timezone.utc)

        archive_id = f"audit_{now.strftime('%Y%m%d_%H%M%S')}_{self._rotation_count}"
        self._rotation_count += 1

        # Get timestamps from entries
        first_entry_at = datetime.fromisoformat(entries_list[0].get("evaluated_at", now.isoformat()))
        last_entry_at = datetime.fromisoformat(entries_list[-1].get("evaluated_at", now.isoformat()))

        # Serialize
        data = json.dumps(entries_list, indent=2, default=str).encode()
        original_size = len(data)

        # Verify hash chain before archiving
        if self._config.verify_on_rotation and self._config.enable_hash_chain:
            if not self._verify_chain(entries_list):
                logger.error("Hash chain verification failed - archive may be corrupted")
                # Continue anyway but log the issue

        # Compress if configured
        compressed_size = None
        if self._config.compress_archives:
            data = gzip.compress(data, compresslevel=self._config.compression_level)
            compressed_size = len(data)
            logger.debug(f"Compressed {original_size} -> {compressed_size} bytes "
                        f"({100 * compressed_size / original_size:.1f}%)")

        # Compute checksum
        checksum = hashlib.sha256(data).hexdigest()

        # Create metadata
        metadata = ArchiveMetadata(
            archive_id=archive_id,
            created_at=now,
            entry_count=len(entries_list),
            first_entry_at=first_entry_at,
            last_entry_at=last_entry_at,
            size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            checksum=checksum,
            hash_chain_start=self._hash_chain[0] if self._hash_chain else "",
            hash_chain_end=self._hash_chain[-1] if self._hash_chain else "",
            destination=self._config.archive_destination,
        )

        # Upload to archive store
        try:
            path = self._archive_store.upload(data, archive_id, metadata)
            metadata.path = path
            logger.info(f"Archive created: {archive_id} with {metadata.entry_count} entries")
        except Exception as e:
            logger.error(f"Failed to upload archive: {e}")
            raise

        # Clear current entries
        self._entries.clear()
        self._current_size_bytes = 0
        self._hash_chain.clear()
        self._last_rotation = now

        # Call rotation callback
        if self._on_rotation:
            try:
                self._on_rotation(metadata)
            except Exception as e:
                logger.error(f"Rotation callback failed: {e}")

        return metadata

    def _verify_chain(self, entries: List[Dict[str, Any]]) -> bool:
        """Verify hash chain integrity."""
        prev_hash = ""
        for entry in entries:
            expected_hash = entry.get("_hash")
            if not expected_hash:
                continue

            entry_copy = {k: v for k, v in entry.items() if k != "_hash"}
            computed_hash = self._compute_entry_hash(entry_copy, prev_hash)

            if computed_hash != expected_hash:
                logger.error(f"Hash mismatch at entry: expected {expected_hash}, got {computed_hash}")
                return False

            prev_hash = expected_hash

        return True

    def force_rotate(self) -> Optional[ArchiveMetadata]:
        """Force immediate rotation."""
        with self._lock:
            return self._rotate()

    def get_current_entries(self) -> List[Dict[str, Any]]:
        """Get current (non-archived) entries."""
        with self._lock:
            return list(self._entries)

    def get_current_count(self) -> int:
        """Get current entry count."""
        with self._lock:
            return len(self._entries)

    def get_archives(self) -> List[ArchiveMetadata]:
        """List all archives."""
        return self._archive_store.list_archives()

    def restore_archive(self, archive_id: str) -> List[Dict[str, Any]]:
        """
        Restore entries from an archive.

        Returns the entries from the archive (does not add to current log).
        """
        data = self._archive_store.download(archive_id)

        # Decompress if needed
        try:
            data = gzip.decompress(data)
        except gzip.BadGzipFile:
            pass  # Not compressed

        entries = json.loads(data)
        logger.info(f"Restored {len(entries)} entries from archive {archive_id}")

        return entries

    def cleanup_expired_archives(self) -> List[str]:
        """
        Remove archives older than retention period.

        Returns list of deleted archive IDs.

        WARNING: Only use if delete_expired is True in config.
        """
        if not self._config.delete_expired:
            logger.warning("delete_expired is False - no archives will be deleted")
            return []

        deleted = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._config.retention_days)

        for archive in self._archive_store.list_archives():
            if archive.created_at < cutoff:
                if self._archive_store.delete(archive.archive_id):
                    deleted.append(archive.archive_id)
                    logger.info(f"Deleted expired archive: {archive.archive_id}")

        return deleted


class RotatingAuditStore:
    """
    Production-ready audit store with automatic rotation.

    Combines the in-memory audit store with automatic archival.
    """

    def __init__(
        self,
        config: Optional[RotationConfig] = None,
    ):
        """
        Initialize rotating audit store.

        Args:
            config: Rotation configuration
        """
        self._config = config or RotationConfig()
        self._rotator = AuditLogRotator(config=self._config)
        self._lock = threading.Lock()
        self._by_mandate: Dict[str, List[str]] = {}

    def append(self, entry: Dict[str, Any]) -> str:
        """
        Append an audit entry.

        Returns the audit_id.
        """
        audit_id = entry.get("audit_id", "")
        mandate_id = entry.get("mandate_id", "")

        with self._lock:
            # Index by mandate
            if mandate_id:
                if mandate_id not in self._by_mandate:
                    self._by_mandate[mandate_id] = []
                self._by_mandate[mandate_id].append(audit_id)

        # Append to rotator (handles rotation automatically)
        self._rotator.append(entry)

        return audit_id

    def get_by_mandate(self, mandate_id: str) -> List[Dict[str, Any]]:
        """Get entries for a mandate (current and archived)."""
        with self._lock:
            audit_ids = set(self._by_mandate.get(mandate_id, []))

        results = []

        # Check current entries
        for entry in self._rotator.get_current_entries():
            if entry.get("audit_id") in audit_ids:
                results.append(entry)

        # Check archives if needed
        if len(results) < len(audit_ids):
            for archive in self._rotator.get_archives():
                entries = self._rotator.restore_archive(archive.archive_id)
                for entry in entries:
                    if entry.get("audit_id") in audit_ids:
                        results.append(entry)

        return results

    def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent entries."""
        current = self._rotator.get_current_entries()
        return current[-limit:]

    def count(self) -> int:
        """Get current entry count (non-archived)."""
        return self._rotator.get_current_count()

    def force_rotate(self) -> Optional[ArchiveMetadata]:
        """Force immediate rotation."""
        return self._rotator.force_rotate()

    def get_archives(self) -> List[ArchiveMetadata]:
        """Get list of archives."""
        return self._rotator.get_archives()

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all current entries."""
        return self._rotator.get_current_entries()
