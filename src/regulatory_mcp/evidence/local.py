"""Private filesystem implementation of the immutable byte-storage boundary."""

import os
from pathlib import Path

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence.backend import StoreError


class LocalByteStore:
    def __init__(self, project_root: Path, settings: Settings):
        self.project_root = project_root.resolve(strict=True)
        self.settings = settings

    def _directory(self) -> int:
        fd = os.open(self.project_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in self.settings.artifact_dir.parts:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass  # Existing directories are verified by the no-follow open below.
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            return fd
        except OSError as exc:
            os.close(fd)
            raise StoreError("STORAGE_REJECTED: cannot open artifact directory") from exc

    def read(self, name: str) -> bytes:
        directory = self._directory()
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            with os.fdopen(fd, "rb") as stream:
                data = stream.read(self.settings.max_download_bytes + 1)
            if len(data) > self.settings.max_download_bytes:
                raise StoreError("STORAGE_REJECTED: stored object exceeds size limit")
            return data
        except OSError as exc:
            raise StoreError("MISSING_OR_UNSAFE_REFERENCE: cannot read stored object") from exc
        finally:
            os.close(directory)

    def write(self, name: str, data: bytes) -> None:
        if len(data) > self.settings.max_download_bytes:
            raise StoreError("STORAGE_REJECTED: object exceeds size limit")
        directory = self._directory()
        try:
            fd = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                mode=0o600,
                dir_fd=directory,
            )
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if self.read(name) != data:
                raise StoreError("IMMUTABLE_CONFLICT: stored object differs") from None
        except OSError as exc:
            raise StoreError("STORAGE_FAILURE: object could not be persisted") from exc
        finally:
            os.close(directory)
