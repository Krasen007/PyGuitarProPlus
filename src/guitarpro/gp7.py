"""
Guitar Pro 7/8 (.gp) file format support.

SPDX-License-Identifier: LGPL-3.0-only
"""

from __future__ import annotations

from typing import Dict, Optional

from .gpif.gp7_container import GP7ReadError, read_gp7, write_gp7
from .gpif.gpif_parser import GpifParseError, GpifParser
from .gpif.gpif_writer import GpifWriter
from .iobase import GPFileBase
from .models import GPException, GpifExtras, Song

__all__ = ['GP7File']


def _find_gpif_entry(files: Dict[str, bytes]) -> Optional[bytes]:
    for candidate in ('Content/score.gpif', 'score.gpif'):
        if candidate in files:
            return files[candidate]
    for name, content in files.items():
        if name.endswith('/score.gpif') or name == 'score.gpif':
            return content
    return None


def _detect_gp8_version(files: Dict[str, bytes], song: Song) -> bool:
    if 'VERSION' in files:
        ver_str = files['VERSION'].decode('utf-8', errors='ignore').strip()
        if ver_str.startswith('8'):
            return True
    if song.format_extras is not None and song.format_extras.gp_version.startswith('8'):
        return True
    return False


class GP7File(GPFileBase):
    """Guitar Pro 7/8 file reader/writer."""

    def readSong(self) -> Song:
        """Read a GP7/GP8 (.gp) file."""
        try:
            files = read_gp7(self.data)
            gpif_content = _find_gpif_entry(files)
            if gpif_content is None:
                raise GP7ReadError("score.gpif not found in GP7/GP8 container")

            song = GpifParser().parse(gpif_content)
            is_gp8 = _detect_gp8_version(files, song)
            song.versionTuple = (8, 0, 0) if is_gp8 else (7, 0, 0)

            extra_files = tuple(
                (name, content)
                for name, content in files.items()
                if name != 'VERSION' and not (name == 'score.gpif' or name.endswith('/score.gpif'))
            )
            if song.format_extras is not None and extra_files:
                song.format_extras = GpifExtras(
                    gp_version=song.format_extras.gp_version,
                    gp_revision=song.format_extras.gp_revision,
                    encoding_description=song.format_extras.encoding_description,
                    automations=song.format_extras.automations,
                    master_track_anacrusis=song.format_extras.master_track_anacrusis,
                    track_rse_xml=song.format_extras.track_rse_xml,
                    track_sounds_xml=song.format_extras.track_sounds_xml,
                    track_automations_xml=song.format_extras.track_automations_xml,
                    container_files=extra_files,
                )
            return song
        except (GP7ReadError, GpifParseError) as exc:
            raise GPException(f"Failed to read GP7/GP8 file: {exc}") from exc

    def writeSong(self, song: Song) -> None:
        """Write a GP7/GP8 (.gp) file."""
        major = self.versionTuple[0] if self.versionTuple and self.versionTuple[0] in (7, 8) else 7
        gpif_bytes = GpifWriter().write(song, target_major_version=major)
        files: Dict[str, bytes] = {
            'VERSION': f'{major}.0'.encode('utf-8'),
            'Content/score.gpif': gpif_bytes,
        }
        if song.format_extras is not None:
            for name, content in song.format_extras.container_files:
                if name in ('VERSION', 'Content/score.gpif', 'score.gpif'):
                    continue
                target_name = name if '/' in name else f'Content/{name}'
                files[target_name] = content
        write_gp7(files, self.data)
