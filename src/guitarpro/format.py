"""
Guitar Pro format detection, format enum, and format handler registry.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import BinaryIO, Callable, Dict, Optional, Tuple, Type, Union

from .iobase import GPFileBase
from .models import GPException

__all__ = [
    'GuitarProFormat',
    'FormatDetectionError',
    'FormatHandler',
    'detect_format',
    'register_format',
    'get_format_handler',
    'get_registered_formats',
    'is_gpif_format',
]


class FormatDetectionError(GPException):
    """Raised when Guitar Pro format detection fails."""


class GuitarProFormat(Enum):
    """Guitar Pro file format identifiers."""

    GP3 = 'gp3'
    GP4 = 'gp4'
    GP5 = 'gp5'
    GP6 = 'gpx'  # GP6 uses .gpx extension with BCFZ/BCFS container
    GP7 = 'gp7'  # GP7 uses .gp extension with ZIP container
    GP8 = 'gp8'  # GP8 uses .gp extension with extended GPIF format


VersionTuple = Tuple[int, int, int]
FormatSniffer = Callable[[bytes, Optional[BinaryIO], Optional[str]], Optional[Tuple[GuitarProFormat, Optional[VersionTuple]]]]


@dataclass(frozen=True)
class FormatHandler:
    """Registry entry describing how to sniff, read, and write a format."""

    format: GuitarProFormat
    extensions: Tuple[str, ...]
    file_cls: Type[GPFileBase]
    default_version: VersionTuple
    sniffer: Optional[FormatSniffer] = None


_FORMAT_REGISTRY: Dict[GuitarProFormat, FormatHandler] = {}


def register_format(handler: FormatHandler) -> None:
    """Register a format handler in the global registry."""
    _FORMAT_REGISTRY[handler.format] = handler


def get_format_handler(fmt: GuitarProFormat) -> FormatHandler:
    """Look up the registered handler for a Guitar Pro format."""
    handler = _FORMAT_REGISTRY.get(fmt)
    if handler is None:
        raise FormatDetectionError(f"Unsupported format: {fmt!r}")
    return handler


def get_registered_formats() -> Dict[GuitarProFormat, FormatHandler]:
    """Return a copy of the registered format handlers."""
    return dict(_FORMAT_REGISTRY)


# Magic bytes for format detection
_MAGIC_BYTES: Tuple[Tuple[bytes, GuitarProFormat], ...] = (
    (b'FICHIER GUITAR PRO v3', GuitarProFormat.GP3),
    (b'FICHIER GUITAR PRO v4', GuitarProFormat.GP4),
    (b'FICHIER GUITAR PRO v5', GuitarProFormat.GP5),
    (b'FICHIER GUITAR PRO L4', GuitarProFormat.GP4),
    (b'CLIPBOARD GUITAR PRO 4', GuitarProFormat.GP4),
    (b'CLIPBOARD GP 5', GuitarProFormat.GP5),
    (b'BCFZ', GuitarProFormat.GP6),
    (b'BCFS', GuitarProFormat.GP6),
    (b'PK\x03\x04', GuitarProFormat.GP7),
)

_EXT_TO_FORMAT: Dict[str, GuitarProFormat] = {
    '.gp3': GuitarProFormat.GP3,
    '.gp4': GuitarProFormat.GP4,
    '.gp5': GuitarProFormat.GP5,
    '.tmp': GuitarProFormat.GP5,
    '.gpx': GuitarProFormat.GP6,
    '.gp': GuitarProFormat.GP7,
}


def _sniff_zip_gp_version(stream: BinaryIO) -> GuitarProFormat:
    """Distinguish GP8 from GP7 inside a ZIP container when possible."""
    pos = stream.tell()
    try:
        data = stream.read()
        stream.seek(pos)
        with zipfile.ZipFile(BytesIO(data), 'r') as zf:
            names = zf.namelist()
            if 'VERSION' in names:
                ver = zf.read('VERSION').decode('utf-8', errors='ignore').strip()
                if ver.startswith('8'):
                    return GuitarProFormat.GP8
            for candidate in ('Content/score.gpif', 'score.gpif'):
                if candidate in names:
                    head = zf.read(candidate)[:512].decode('utf-8', errors='ignore')
                    if '<GPVersion>8</GPVersion>' in head:
                        return GuitarProFormat.GP8
                    break
    except Exception:
        try:
            stream.seek(pos)
        except Exception:
            pass
    return GuitarProFormat.GP7


def detect_format(
    stream: Union[BinaryIO, str, bytes, os.PathLike[str], os.PathLike[bytes]],
    filename: Optional[str] = None,
) -> Tuple[GuitarProFormat, Optional[VersionTuple]]:
    """
    Detect Guitar Pro format from a path or binary stream.

    :param stream: Path to a GP file or a seekable binary stream
    :param filename: Optional filename for extension-based fallback
    :return: Tuple of (GuitarProFormat, version_tuple or None)
    :raises FormatDetectionError: If format cannot be detected
    """
    if isinstance(stream, (str, bytes, os.PathLike)):
        path_str = os.fspath(stream)
        inferred_name = filename or (
            path_str.decode('utf-8', errors='ignore') if isinstance(path_str, bytes) else path_str
        )
        try:
            with open(stream, 'rb') as fp:
                return detect_format(fp, filename=inferred_name)
        except OSError as exc:
            raise FormatDetectionError(f"Cannot open file for format detection: {exc}") from exc

    start_pos = stream.tell()
    try:
        header = stream.read(64)
        stream.seek(start_pos)

        if not header:
            raise FormatDetectionError("Empty file or cannot read header")

        for magic, fmt in _MAGIC_BYTES:
            # GP3/4/5 headers are 1-byte length-prefixed (e.g. b'\x18FICHIER GUITAR PRO v5.00')
            if header.startswith(magic) or (
                fmt in (GuitarProFormat.GP3, GuitarProFormat.GP4, GuitarProFormat.GP5)
                and header[1:].startswith(magic)
            ):
                if fmt in (GuitarProFormat.GP3, GuitarProFormat.GP4, GuitarProFormat.GP5):
                    return fmt, _extract_version(header)
                if fmt == GuitarProFormat.GP7:
                    detected = _sniff_zip_gp_version(stream)
                    default_ver = (8, 0, 0) if detected == GuitarProFormat.GP8 else (7, 0, 0)
                    return detected, default_ver
                if fmt == GuitarProFormat.GP6:
                    return fmt, (6, 0, 0)
                return fmt, None

        effective_name = filename or getattr(stream, 'name', None)
        if effective_name:
            if isinstance(effective_name, bytes):
                effective_name = effective_name.decode('utf-8', errors='ignore')
            ext = os.path.splitext(effective_name)[1].lower()
            if ext in _EXT_TO_FORMAT:
                fmt = _EXT_TO_FORMAT[ext]
                handler = _FORMAT_REGISTRY.get(fmt)
                return fmt, (handler.default_version if handler else None)

        raise FormatDetectionError(f"Unknown format, header: {header[:16].hex()}")
    except FormatDetectionError:
        stream.seek(start_pos)
        raise
    except Exception as exc:
        try:
            stream.seek(start_pos)
        except Exception:
            pass
        raise FormatDetectionError(f"Format detection failed: {exc}") from exc


def _extract_version(header: bytes) -> Optional[VersionTuple]:
    """Extract version tuple from GP3/4/5 header string."""
    try:
        # GP3/4/5 headers are length-prefixed (1 byte) followed by up to 30 chars
        raw_str = header[1:31] if header[0] < 32 else header[:32]
        header_str = raw_str.decode('latin-1', errors='ignore')

        if 'CLIPBOARD' in header_str:
            if 'GP 5.0' in header_str:
                return (5, 0, 0)
            if 'GP 5.1' in header_str:
                return (5, 1, 0)
            if 'GP 5.2' in header_str:
                return (5, 2, 0)
            if '4.0' in header_str or '4.' in header_str:
                return (4, 0, 6)

        if ' v' in header_str:
            version_part = header_str.split(' v')[1].split('\x00')[0].strip()
            # Handle "v3.00", "v4.06", "v5.10"
            digits = ''
            for ch in version_part:
                if ch.isdigit() or ch == '.':
                    digits += ch
                else:
                    break
            parts = digits.split('.')
            if len(parts) == 2 and len(parts[1]) == 2:
                return (int(parts[0]), int(parts[1][0]), int(parts[1][1]))
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                patch = int(parts[2]) if len(parts) > 2 else 0
                return (major, minor, patch)
    except Exception:
        pass

    return None


def is_gpif_format(fmt: GuitarProFormat) -> bool:
    """Check if format uses GPIF (XML-based) format."""
    return fmt in (GuitarProFormat.GP6, GuitarProFormat.GP7, GuitarProFormat.GP8)
