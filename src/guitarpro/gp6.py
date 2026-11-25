"""
Guitar Pro 6 (.gpx) file format support.

SPDX-License-Identifier: LGPL-3.0-only
"""

from __future__ import annotations

from typing import Dict

from .gp6_container_metadata import update_container_metadata_for_song
from .gpif.gp6_container import GPXReadError, read_gpx, write_gpx
from .gpif.gpif_parser import GpifParseError, GpifParser
from .gpif.gpif_writer import GpifWriter
from .iobase import GPFileBase
from .models import GPException, GpifExtras, Song

__all__ = ['GP6File']


class GP6File(GPFileBase):
    """Guitar Pro 6 file reader/writer."""

    def readSong(self) -> Song:
        """Read a GP6 (.gpx) file."""
        try:
            files = read_gpx(self.data)
            gpif_content = files.get('score.gpif')
            if gpif_content is None:
                raise GPXReadError("score.gpif not found in GPX container")

            song = GpifParser().parse(gpif_content)
            song.versionTuple = (6, 0, 0)

            extra_files = tuple(
                (name, content)
                for name, content in files.items()
                if name != 'score.gpif'
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
        except (GPXReadError, GpifParseError) as exc:
            raise GPException(f"Failed to read GP6 file: {exc}") from exc

    def writeSong(self, song: Song) -> None:
        """Write a GP6 (.gpx) file."""
        # Only regenerate container metadata if track count has changed
        should_update = True
        if song.format_extras is not None:
            # Check if track count in existing metadata matches current track count
            for name, content in song.format_extras.container_files:
                if name == 'misc.xml':
                    try:
                        current_misc = content.decode('utf-8')
                        expected_count = f'<PreferredTrackCount>{len(song.tracks)}</PreferredTrackCount>'
                        if expected_count in current_misc:
                            should_update = False
                    except (UnicodeDecodeError, AttributeError):
                        pass
                    break
        
        if should_update:
            update_container_metadata_for_song(song)
        
        gpif_bytes = GpifWriter().write(song, target_major_version=6)
        files: Dict[str, bytes] = {'score.gpif': gpif_bytes}
        if song.format_extras is not None:
            for name, content in song.format_extras.container_files:
                if name not in ('score.gpif', 'Content/score.gpif', 'VERSION') and not name.endswith('/'):
                    files[name] = content
        write_gpx(files, self.data, compress=True)
