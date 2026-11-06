"""Byte-storage boundary; immutable generated keys, bounded reads and writes."""

from typing import Protocol


class StoreError(ValueError):
    """An explicit storage, integrity, or evidence-reference failure."""


class ByteStore(Protocol):
    """Create-only objects. Repeating identical writes succeeds; conflicts fail."""

    def read(self, name: str) -> bytes: ...

    def write(self, name: str, data: bytes) -> None: ...
