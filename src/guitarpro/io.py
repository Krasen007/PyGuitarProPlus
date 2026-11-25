from __future__ import annotations

import os
from typing import BinaryIO, Optional, Tuple, Union

from .format import (
    FormatDetectionError,
    FormatHandler,
    GuitarProFormat,
    VersionTuple,
    detect_format,
    get_format_handler,
    register_format,
)
from .gp3 import GP3File
from .gp4 import GP4File
from .gp5 import GP5File
from .gp6 import GP6File
from .gp7 import GP7File
from .iobase import GPFileBase
from .models import GPException, Song

__all__ = ('parse', 'write', 'detect_format', 'GuitarProFormat', 'FormatDetectionError')

_GPFILES = {
    'FICHIER GUITAR PRO v3.00': ((3, 0, 0), GP3File),

    'FICHIER GUITAR PRO v4.00': ((4, 0, 0), GP4File),
    'FICHIER GUITAR PRO v4.06': ((4, 0, 6), GP4File),
    'FICHIER GUITAR PRO L4.06': ((4, 0, 6), GP4File),
    'CLIPBOARD GUITAR PRO 4.0 [c6]': ((4, 0, 6), GP4File),

    'FICHIER GUITAR PRO v5.00': ((5, 0, 0), GP5File),
    'FICHIER GUITAR PRO v5.10': ((5, 1, 0), GP5File),
    'CLIPBOARD GP 5.0': ((5, 0, 0), GP5File),
    'CLIPBOARD GP 5.1': ((5, 1, 0), GP5File),
    'CLIPBOARD GP 5.2': ((5, 2, 0), GP5File),
}

_VERSIONS = {
    # (versionTuple, isClipboard): versionString,
    ((3, 0, 0), False): 'FICHIER GUITAR PRO v3.00',

    ((4, 0, 0), False): 'FICHIER GUITAR PRO v4.00',
    ((4, 0, 6), False): 'FICHIER GUITAR PRO v4.06',
    ((4, 0, 6), True): 'CLIPBOARD GUITAR PRO 4.0 [c6]',

    ((5, 0, 0), False): 'FICHIER GUITAR PRO v5.00',
    ((5, 1, 0), False): 'FICHIER GUITAR PRO v5.10',
    ((5, 2, 0), False): 'FICHIER GUITAR PRO v5.10',  # sic
    ((5, 0, 0), True): 'CLIPBOARD GP 5.0',
    ((5, 1, 0), True): 'CLIPBOARD GP 5.1',
    ((5, 2, 0), True): 'CLIPBOARD GP 5.2',
}

_EXT_VERSIONS = {
    'gp3': (3, 0, 0),
    'gp4': (4, 0, 6),
    'gp5': (5, 1, 0),
    'gpx': (6, 0, 0),
    'gp': (7, 0, 0),
    'tmp': (5, 2, 0),
}

# Register all supported formats in the central registry
for _handler in (
    FormatHandler(GuitarProFormat.GP3, ('.gp3',), GP3File, (3, 0, 0)),
    FormatHandler(GuitarProFormat.GP4, ('.gp4',), GP4File, (4, 0, 6)),
    FormatHandler(GuitarProFormat.GP5, ('.gp5', '.tmp'), GP5File, (5, 1, 0)),
    FormatHandler(GuitarProFormat.GP6, ('.gpx',), GP6File, (6, 0, 0)),
    FormatHandler(GuitarProFormat.GP7, ('.gp',), GP7File, (7, 0, 0)),
    FormatHandler(GuitarProFormat.GP8, ('.gp',), GP7File, (8, 0, 0)),
):
    register_format(_handler)


def parse(
    stream: Union[BinaryIO, str, bytes, os.PathLike[str], os.PathLike[bytes]],
    encoding: str = 'cp1252',
    format: Optional[GuitarProFormat] = None,
    version: Optional[VersionTuple] = None,
) -> Song:
    """Open a GP file and read its contents.

    :param stream: path to a GP file or file-like object.
    :param encoding: decode strings in tablature using this charset.
        Given encoding must be an 8-bit charset.
    :param format: explicitly override format detection. If None, format
        is auto-detected from file header and extension.
    :param version: optional explicit version tuple override.
    """
    gpfile, shouldClose = _open(
        None,
        stream,
        'rb',
        version=version,
        encoding=encoding,
        format_override=format,
    )
    try:
        return gpfile.readSong()
    finally:
        if shouldClose:
            gpfile.close()


def write(
    song: Song,
    stream: Union[BinaryIO, str, bytes, os.PathLike[str], os.PathLike[bytes]],
    version: Optional[VersionTuple] = None,
    encoding: str = 'cp1252',
    format: Optional[GuitarProFormat] = None,
) -> None:
    """Write a song into GP file.

    :param song: a song to write.
    :param stream: path to save GP file or file-like object.
    :param version: explicitly set version of GP file to save, e.g.
        ``(5, 1, 0)``.
    :param encoding: encode strings into given 8-bit charset.
    :param format: explicitly override target format (e.g. ``GuitarProFormat.GP6``).
    """
    gpfile, shouldClose = _open(
        song,
        stream,
        'wb',
        version=version,
        encoding=encoding,
        format_override=format,
    )
    try:
        gpfile.writeSong(song)
    finally:
        if shouldClose:
            gpfile.close()


def _format_from_version(version: VersionTuple) -> GuitarProFormat:
    major = version[0]
    if major == 3:
        return GuitarProFormat.GP3
    if major == 4:
        return GuitarProFormat.GP4
    if major == 5:
        return GuitarProFormat.GP5
    if major == 6:
        return GuitarProFormat.GP6
    if major == 7:
        return GuitarProFormat.GP7
    if major == 8:
        return GuitarProFormat.GP8
    raise GPException(f"unsupported version: {version}")


def _open(
    song: Optional[Song],
    stream: Union[BinaryIO, str, bytes, os.PathLike[str], os.PathLike[bytes]],
    mode: str = 'rb',
    version: Optional[VersionTuple] = None,
    encoding: Optional[str] = None,
    format_override: Optional[GuitarProFormat] = None,
) -> Tuple[GPFileBase, bool]:
    """Open a GP file path for reading or writing."""
    if mode not in ('rb', 'wb'):
        raise ValueError(f"cannot read or write unless in binary mode, not '{mode}'")

    shouldClose = False
    if isinstance(stream, (str, bytes, os.PathLike)):
        fp = open(stream, mode)
        shouldClose = True
        filename = os.fspath(stream)
        if isinstance(filename, bytes):
            filename = filename.decode('utf-8', errors='ignore')
    else:
        fp = stream
        raw_name = getattr(fp, 'name', '<file>')
        filename = raw_name.decode('utf-8', errors='ignore') if isinstance(raw_name, bytes) else str(raw_name)

    try:
        if mode == 'rb':
            if format_override is not None:
                detected_format = format_override
                versionTuple = version
            else:
                detected_format, detected_version = detect_format(fp, filename)
                versionTuple = version or detected_version

            handler = get_format_handler(detected_format)
            GPFile = handler.file_cls

            if detected_format in (GuitarProFormat.GP3, GuitarProFormat.GP4, GuitarProFormat.GP5):
                gpfilebase = GPFileBase(fp, encoding)
                versionString = gpfilebase.readVersion()
                parsed_version, _ = getVersionAndGPFile(versionString)
                gpfile = GPFile(fp, encoding, version=versionString, versionTuple=versionTuple or parsed_version)
            else:
                gpfile = GPFile(fp, encoding, version=None, versionTuple=versionTuple or handler.default_version)

            return gpfile, shouldClose

        # mode == 'wb'
        assert song is not None
        if format_override is not None:
            handler = get_format_handler(format_override)
            target_version = version or handler.default_version
            target_format = format_override
        else:
            target_version = version
            if target_version is None:
                target_version = song.versionTuple
            if target_version is None:
                target_version = guessVersionByExtension(filename)
            target_format = _format_from_version(target_version)
            handler = get_format_handler(target_format)

        if target_format in (GuitarProFormat.GP6, GuitarProFormat.GP7, GuitarProFormat.GP8):
            gpfile = handler.file_cls(fp, encoding, version=None, versionTuple=target_version)
            return gpfile, shouldClose

        isClipboard = song.clipboard is not None
        versionString = _VERSIONS[(target_version, isClipboard)]
        parsed_version, GPFile = getVersionAndGPFile(versionString)
        gpfile = GPFile(fp, encoding, version=versionString, versionTuple=parsed_version)
        return gpfile, shouldClose
    except Exception:
        if shouldClose:
            fp.close()
        raise


def getVersionAndGPFile(versionString):
    try:
        return _GPFILES[versionString]
    except KeyError:
        raise GPException(f"unsupported version '{versionString}'")


def guessVersionByExtension(filename):
    __, ext = os.path.splitext(filename)
    ext = ext.lstrip('.').lower()
    version = _EXT_VERSIONS.get(ext)
    if version is None:
        version = _EXT_VERSIONS['gp5']
    return version
