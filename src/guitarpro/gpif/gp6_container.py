"""
Guitar Pro 6 (.gpx) container format support (BCFZ/BCFS).

This module handles the BCFZ and BCFS container formats used by Guitar Pro 6.
Implementation derived from alphaTab's GpxFileSystem.ts and BitReader.ts.

SPDX-License-Identifier: MPL-2.0
Based on: https://github.com/CoderLine/alphaTab (GpxFileSystem.ts, BitReader.ts)
"""

from __future__ import annotations

import struct
from io import BytesIO
from typing import BinaryIO, Callable, Dict, Optional

__all__ = ['read_gpx', 'write_gpx', 'GPXReadError']

SECTOR_SIZE = 0x1000
HEADER_BCFS = b'BCFS'
HEADER_BCFZ = b'BCFZ'
DEFAULT_MAX_DECODING_BUFFER_SIZE = 64 * 1024 * 1024  # 64 MiB


class GPXReadError(Exception):
    """Raised when GPX container cannot be read."""


class _EndOfReaderError(Exception):
    pass


class _BitReader:
    """Bitwise reader ported from alphaTab's BitReader.ts."""

    def __init__(self, source: BinaryIO) -> None:
        self._source = source
        self._current_byte = 0
        self._position = 8

    def read_byte(self) -> int:
        return self.read_bits(8)

    def read_bytes(self, count: int) -> bytes:
        return bytes(self.read_byte() & 0xFF for _ in range(count))

    def read_bits(self, count: int) -> int:
        bits = 0
        for i in range(count - 1, -1, -1):
            bits |= self.read_bit() << i
        return bits

    def read_bits_reversed(self, count: int) -> int:
        bits = 0
        for i in range(count):
            bits |= self.read_bit() << i
        return bits

    def read_bit(self) -> int:
        if self._position >= 8:
            b = self._source.read(1)
            if not b:
                raise _EndOfReaderError()
            self._current_byte = b[0]
            self._position = 0
        value = (self._current_byte >> (7 - self._position)) & 0x01
        self._position += 1
        return value

    def read_all(self) -> bytes:
        out = bytearray()
        try:
            while True:
                out.append(self.read_byte() & 0xFF)
        except _EndOfReaderError:
            pass
        return bytes(out)


class _BitWriter:
    """Bitwise writer for linear literal-only BCFZ output."""

    def __init__(self) -> None:
        self._out = bytearray()
        self._current_byte = 0
        self._position = 0

    def write_bit(self, bit: int) -> None:
        if bit & 1:
            self._current_byte |= 1 << (7 - self._position)
        self._position += 1
        if self._position == 8:
            self._out.append(self._current_byte)
            self._current_byte = 0
            self._position = 0

    def write_bits_reversed(self, value: int, count: int) -> None:
        for i in range(count):
            self.write_bit((value >> i) & 1)

    def write_byte(self, byte_val: int) -> None:
        if self._position == 0:
            self._out.append(byte_val & 0xFF)
        else:
            for i in range(7, -1, -1):
                self.write_bit((byte_val >> i) & 1)

    def finish(self) -> bytes:
        if self._position > 0:
            self._out.append(self._current_byte)
            self._current_byte = 0
            self._position = 0
        return bytes(self._out)


def _decompress_bcfz(
    src: _BitReader,
    skip_header: bool = True,
    max_decoding_buffer_size: int = DEFAULT_MAX_DECODING_BUFFER_SIZE,
) -> bytes:
    """Decompress BCFZ bitstream into BCFS filesystem bytes."""
    length_bytes = src.read_bytes(4)
    if len(length_bytes) < 4:
        raise GPXReadError("GPX container is truncated (missing expected length)")
    expected_length = struct.unpack('<i', length_bytes)[0]
    if expected_length < 0 or expected_length > max_decoding_buffer_size:
        raise GPXReadError(
            f"GPX container expected length {expected_length} exceeds limit {max_decoding_buffer_size}"
        )

    uncompressed = bytearray()
    try:
        while len(uncompressed) < expected_length:
            flag = src.read_bits(1)
            if flag == 1:
                word_size = src.read_bits(4)
                offset = src.read_bits_reversed(word_size)
                size = src.read_bits_reversed(word_size)
                source_pos = len(uncompressed) - offset
                if source_pos < 0:
                    raise GPXReadError("Invalid BCFZ back-reference offset")
                to_read = min(offset, size)
                uncompressed.extend(uncompressed[source_pos : source_pos + to_read])
            else:
                size = src.read_bits_reversed(2)
                for _ in range(size):
                    uncompressed.append(src.read_byte())
    except _EndOfReaderError:
        pass

    result_offset = 4 if skip_header else 0
    if len(uncompressed) < result_offset:
        raise GPXReadError("GPX container is truncated")
    return bytes(uncompressed[result_offset:])


def _read_uncompressed_block(
    data: bytes,
    file_filter: Optional[Callable[[str], bool]] = None,
) -> Dict[str, bytes]:
    """Read BCFS 4KB-sector filesystem into a filename -> bytes mapping."""
    files: Dict[str, bytes] = {}
    offset = SECTOR_SIZE
    data_len = len(data)

    while offset + 3 < data_len:
        entry_type = struct.unpack_from('<i', data, offset)[0]
        if entry_type == 2:
            data_pointer_offset = offset + 0x94
            if data_pointer_offset + 4 > data_len:
                raise GPXReadError("GPX file entry is truncated")

            raw_name = data[offset + 0x04 : offset + 0x04 + 127]
            nul_idx = raw_name.find(0)
            if nul_idx != -1:
                raw_name = raw_name[:nul_idx]
            file_name = raw_name.decode('ascii', errors='replace')

            file_size = struct.unpack_from('<i', data, offset + 0x8C)[0]
            if file_size < 0 or file_size > data_len:
                raise GPXReadError(f"GPX file entry '{file_name}' has an invalid size: {file_size}")

            store_file = file_filter is None or file_filter(file_name)
            file_data = bytearray() if store_file else None

            sector_count = 0
            while True:
                pointer_offset = data_pointer_offset + 4 * sector_count
                sector_count += 1
                if pointer_offset + 4 > data_len:
                    raise GPXReadError(f"GPX file entry '{file_name}' has an unterminated sector list")
                sector = struct.unpack_from('<i', data, pointer_offset)[0]
                if sector == 0:
                    break
                sector_offset = sector * SECTOR_SIZE
                if sector < 0 or sector_offset >= data_len:
                    raise GPXReadError(
                        f"GPX file entry '{file_name}' points to sector {sector} outside of the container"
                    )
                offset = max(offset, sector_offset)
                if store_file and file_data is not None and len(file_data) < file_size:
                    end_offset = min(sector_offset + SECTOR_SIZE, data_len)
                    file_data.extend(data[sector_offset:end_offset])

            if store_file and file_data is not None:
                files[file_name] = bytes(file_data[:file_size])

        offset += SECTOR_SIZE

    return files


def read_gpx(
    stream: BinaryIO,
    file_filter: Optional[Callable[[str], bool]] = None,
    max_decoding_buffer_size: int = DEFAULT_MAX_DECODING_BUFFER_SIZE,
) -> Dict[str, bytes]:
    """
    Read a GP6 .gpx file and extract its contents.

    The .gpx format is a custom container format with either:
    - BCFZ header (LZ-compressed BCFS filesystem)
    - BCFS header (uncompressed 4KB-sector filesystem)

    :param stream: Binary stream containing GPX data
    :param file_filter: Optional predicate accepting a filename and returning True to retain it
    :param max_decoding_buffer_size: Maximum allowed decompressed size in bytes
    :return: Dictionary mapping filenames to their byte content
    :raises GPXReadError: If the container cannot be read
    """
    src = _BitReader(stream)
    try:
        header = src.read_bytes(4)
    except _EndOfReaderError as exc:
        raise GPXReadError("Empty GPX stream") from exc

    if header == HEADER_BCFZ:
        bcfs_body = _decompress_bcfz(
            src,
            skip_header=True,
            max_decoding_buffer_size=max_decoding_buffer_size,
        )
        return _read_uncompressed_block(bcfs_body, file_filter=file_filter)
    if header == HEADER_BCFS:
        bcfs_body = src.read_all()
        return _read_uncompressed_block(bcfs_body, file_filter=file_filter)

    raise GPXReadError(f"Unsupported GPX header: {header!r}")


def _build_bcfs(files: Dict[str, bytes]) -> bytes:
    """Build a valid BCFS 4KB-sector filesystem image (including 'BCFS' header)."""
    # Header (4 bytes) + Sector 0 (0x1000 bytes of 0xFF padding)
    buf = bytearray()
    buf.extend(HEADER_BCFS)
    buf.extend(b'\xff' * SECTOR_SIZE)

    next_sector = 1
    for name, content in files.items():
        name_bytes = name.encode('utf-8')[:126]
        file_size = len(content)
        data_sector_count = max(1, (file_size + SECTOR_SIZE - 1) // SECTOR_SIZE)

        # Allocate entry sector, then data sectors immediately after it
        entry_sector = next_sector
        first_data_sector = entry_sector + 1
        next_sector = first_data_sector + data_sector_count

        entry = bytearray(SECTOR_SIZE)
        struct.pack_into('<i', entry, 0x00, 2)  # entryType = 2 (file)
        entry[0x04 : 0x04 + len(name_bytes)] = name_bytes
        struct.pack_into('<i', entry, 0x8C, file_size)

        max_pointers = (SECTOR_SIZE - 0x94) // 4 - 1
        if data_sector_count > max_pointers:
            raise GPXReadError(f"File '{name}' is too large for single-sector GPX entry table")

        for i in range(data_sector_count):
            struct.pack_into('<i', entry, 0x94 + 4 * i, first_data_sector + i)
        struct.pack_into('<i', entry, 0x94 + 4 * data_sector_count, 0)

        buf.extend(entry)

        # Write data sectors
        for i in range(data_sector_count):
            chunk = content[i * SECTOR_SIZE : (i + 1) * SECTOR_SIZE]
            buf.extend(chunk)
            if len(chunk) < SECTOR_SIZE:
                buf.extend(b'\x00' * (SECTOR_SIZE - len(chunk)))

    return bytes(buf)


def _compress_bcfz_literal(bcfs_data: bytes) -> bytes:
    """Encode BCFS bytes into a linear literal-only BCFZ container."""
    out = BytesIO()
    out.write(HEADER_BCFZ)
    out.write(struct.pack('<i', len(bcfs_data)))

    bw = _BitWriter()
    pos = 0
    total = len(bcfs_data)
    while pos < total:
        chunk_len = min(3, total - pos)
        bw.write_bit(0)  # literal flag
        bw.write_bits_reversed(chunk_len, 2)
        for i in range(chunk_len):
            bw.write_byte(bcfs_data[pos + i])
        pos += chunk_len

    out.write(bw.finish())
    return out.getvalue()


def write_gpx(files: Dict[str, bytes], stream: BinaryIO, compress: bool = True) -> None:
    """
    Write files into a GP6 .gpx container format.

    :param files: Dictionary mapping filenames to their byte content
    :param stream: Binary stream to write to
    :param compress: If True, write a literal-only BCFZ container; otherwise write raw BCFS
    """
    bcfs_data = _build_bcfs(files)
    if compress:
        stream.write(_compress_bcfz_literal(bcfs_data))
    else:
        stream.write(bcfs_data)
