"""List and extract a PyInstaller CArchive without executing it.

Usage: python tools/extract_pyinstaller.py ccna.exe extracted
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path


MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
COOKIE_SIZE = 88
TOC_HEADER = struct.Struct("!IIIIBB")


def safe_path(root: Path, name: str) -> Path:
    normalized = Path(*[part for part in name.replace("\\", "/").split("/") if part not in ("", ".", "..")])
    if not normalized.parts:
        raise ValueError("empty archive path")
    return root / normalized


def read_cookie(payload: bytes) -> tuple[int, int, int]:
    start = len(payload) - COOKIE_SIZE
    cookie = payload[start:]
    if len(cookie) != COOKIE_SIZE or cookie[:8] != MAGIC:
        raise ValueError("PyInstaller 2.1+ CArchive cookie not found at end of file")
    package_length, toc_offset, toc_length, _pyvers = struct.unpack("!IIII", cookie[8:24])
    archive_start = len(payload) - package_length
    if archive_start < 0 or toc_offset + toc_length > package_length:
        raise ValueError("invalid CArchive offsets")
    return archive_start, toc_offset, toc_length


def extract(source: Path, destination: Path) -> list[tuple[str, str, int]]:
    payload = source.read_bytes()
    archive_start, toc_offset, toc_length = read_cookie(payload)
    toc = memoryview(payload)[archive_start + toc_offset: archive_start + toc_offset + toc_length]
    destination.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str, int]] = []
    cursor = 0
    while cursor < len(toc):
        if len(toc) - cursor < TOC_HEADER.size:
            raise ValueError("truncated table-of-contents entry")
        entry_length, offset, compressed_size, uncompressed_size, compressed, typecode = TOC_HEADER.unpack(toc[cursor:cursor + TOC_HEADER.size])
        if entry_length < TOC_HEADER.size + 1 or cursor + entry_length > len(toc):
            raise ValueError("invalid table-of-contents entry length")
        raw_name = bytes(toc[cursor + TOC_HEADER.size:cursor + entry_length]).split(b"\0", 1)[0]
        name = raw_name.decode("utf-8", "surrogateescape")
        data_start = archive_start + offset
        data_end = data_start + compressed_size
        if data_start < archive_start or data_end > len(payload):
            raise ValueError(f"invalid data range for {name!r}")
        data = payload[data_start:data_end]
        if compressed:
            data = zlib.decompress(data)
        if len(data) != uncompressed_size:
            raise ValueError(f"length mismatch for {name!r}")
        kind = chr(typecode)
        output = safe_path(destination, name)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        rows.append((name, kind, len(data)))
        cursor += entry_length
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    rows = extract(args.source, args.destination)
    print(f"Extracted {len(rows)} CArchive entries to {args.destination}")
    for name, kind, length in rows:
        print(f"{kind}\t{length}\t{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
