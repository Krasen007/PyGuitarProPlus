"""
Guitar Pro 7/8 (.gp) container format support (ZIP).

This module handles the ZIP container format used by Guitar Pro 7 and 8.

SPDX-License-Identifier: MPL-2.0
"""

import zipfile
from io import BytesIO
from typing import Dict, BinaryIO

__all__ = ['read_gp7', 'write_gp7', 'GP7ReadError']


class GP7ReadError(Exception):
    """Raised when GP7/GP8 container cannot be read."""
    pass


def read_gp7(stream: BinaryIO) -> Dict[str, bytes]:
    """
    Read a GP7/GP8 .gp file and extract its contents.
    
    The .gp format is a standard ZIP archive containing score.gpif and other files.
    
    :param stream: Binary stream containing GP7/GP8 data
    :return: Dictionary mapping filenames to their byte content
    :raises GP7ReadError: If the container cannot be read
    """
    try:
        with zipfile.ZipFile(stream, 'r') as zf:
            files = {}
            for name in zf.namelist():
                files[name] = zf.read(name)
            return files
    except zipfile.BadZipFile as e:
        raise GP7ReadError(f"Invalid ZIP format: {e}")
    except Exception as e:
        raise GP7ReadError(f"Failed to read GP7/GP8 container: {e}")


def write_gp7(files: Dict[str, bytes], stream: BinaryIO, compression: int = zipfile.ZIP_DEFLATED):
    """
    Write files into a GP7/GP8 .gp container format (ZIP).
    
    :param files: Dictionary mapping filenames to their byte content
    :param stream: Binary stream to write to
    :param compression: ZIP compression method (default: ZIP_DEFLATED)
    """
    with zipfile.ZipFile(stream, 'w', compression=compression) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
