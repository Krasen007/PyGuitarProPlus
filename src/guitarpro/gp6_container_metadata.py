"""
Generator for GP6/GPX container metadata files.

These binary and XML files control track visibility and layout in Guitar Pro 6/7.
When tracks are added or removed from a Song, the container metadata must be
regenerated to match, otherwise Guitar Pro may display the wrong track count.

SPDX-License-Identifier: LGPL-3.0-only
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Song

__all__ = ['generate_misc_xml', 'generate_part_configuration', 'generate_layout_configuration']


def generate_misc_xml(track_count: int) -> bytes:
    """
    Generate misc.xml with correct PreferredTrackCount.
    
    Args:
        track_count: Number of tracks in the song
        
    Returns:
        UTF-8 encoded XML bytes
    """
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<MISC>
\t<TracksView>
\t\t<PreferredTrackCount>{track_count}</PreferredTrackCount>
\t</TracksView>
</MISC>'''
    return xml.encode('utf-8')


def generate_part_configuration(track_count: int) -> bytes:
    """
    Generate PartConfiguration binary based on track count.
    
    This binary format appears to encode part visibility and ordering.
    The structure is reverse-engineered from Guitar Pro 6 files.
    
    Validated formats (extracted from Guitar Pro-generated files):
    - 1 track (20 bytes): 00000002 00000000 01030000 00000103 00000001
    - 2 tracks (27 bytes): 00000003 00000000 02030100 00000001 03000000 00010100 000001
    
    Structure interpretation:
    - Header: track_count+1 (int32 BE), padding (int32 BE = 0)
    - For 1 track: two 6-byte view segments
    - For 2+ tracks: variable-length indices section + view segments per track
    
    Note: 3+ track formats are extrapolated from 1-2 track patterns. While the
    extrapolation follows the observed pattern, it has not been validated against
    Guitar Pro-generated files with 3+ tracks. The generated binary may require
    adjustment if Guitar Pro rejects it.
    
    Args:
        track_count: Number of tracks in the song
        
    Returns:
        Big-endian binary configuration
    """
    if track_count == 0:
        # Empty configuration for no tracks
        return struct.pack('>I', 1) + b'\x00' * 16
    
    # Start with count+1 header
    parts = [struct.pack('>I', track_count + 1), b'\x00\x00\x00\x00']
    
    if track_count == 1:
        # Single track pattern (reverse-engineered from examples)
        parts.extend([
            b'\x01\x03\x00\x00\x00\x00',
            b'\x01\x03\x00\x00\x00\x01',
        ])
    elif track_count == 2:
        # Two tracks pattern (validated against Guitar Pro files)
        parts.extend([
            b'\x02\x03\x01\x00\x00\x00\x00',
            b'\x01\x03\x00\x00\x00\x00',
            b'\x01\x01\x00\x00\x00\x01',
        ])
    else:
        # For 3+ tracks, extrapolated pattern - WARNING: NOT VALIDATED
        # The structure may not match Guitar Pro's expectations for the
        # "view" encoding. If Guitar Pro rejects files with 3+ tracks,
        # this section will need to be rewritten based on actual GP-generated
        # examples or through trial-and-error testing with Guitar Pro.
        #
        # TODO: Validate this against a Guitar Pro-generated file with 3+ tracks
        # or test by opening the generated file in Guitar Pro.
        
        # First track marker
        track_indices = bytes([track_count]) + b'\x03' + bytes(range(track_count - 1, 0, -1)) + b'\x00' * max(0, 6 - track_count)
        parts.append(track_indices)
        
        # Per-track segments
        for i in range(track_count):
            if i == 0:
                parts.append(b'\x01\x03\x00\x00\x00\x00')
            else:
                parts.append(b'\x01\x01\x00\x00\x00\x01')
    
    return b''.join(parts)


def generate_layout_configuration(track_count: int) -> bytes:
    """
    Generate LayoutConfiguration binary based on track count.
    
    This appears to control track layout in the GUI.
    
    Validated formats (extracted from Guitar Pro-generated files):
    - 1 track (12 bytes): 00000004 0000ffff 00000000
    - 2 tracks (14 bytes): 00000004 0300ffff ffff0000 0000
    
    Structure interpretation:
    - Starts with 0x00000004 (int32 BE constant)
    - Followed by track visibility markers
    - Pattern for 2+ tracks: marker byte (track_count*2 - 3), 0x00, then 0xffff repeated
    
    Note: 3+ track formats are extrapolated from 1-2 track patterns. While the
    extrapolation follows the observed pattern, it has not been validated against
    Guitar Pro-generated files with 3+ tracks. The generated binary may require
    adjustment if Guitar Pro rejects it.
    
    Args:
        track_count: Number of tracks in the song
        
    Returns:
        Big-endian binary configuration
    """
    if track_count == 0:
        return struct.pack('>I', 4) + b'\x00\x00\xff\xff\x00\x00\x00\x00'
    
    parts = [struct.pack('>I', 4)]
    
    if track_count == 1:
        parts.append(b'\x00\x00\xff\xff\x00\x00\x00\x00')
    elif track_count == 2:
        parts.append(b'\x03\x00\xff\xff\xff\xff\x00\x00\x00\x00')
    else:
        # For 3+ tracks: extrapolated pattern - WARNING: NOT VALIDATED
        # The marker byte formula (track_count * 2 - 3) may not be correct
        # for all track counts. If Guitar Pro rejects files with 3+ tracks,
        # this calculation will need adjustment based on actual examples.
        #
        # TODO: Validate this against a Guitar Pro-generated file with 3+ tracks
        marker_byte = (track_count * 2) - 3
        parts.append(bytes([marker_byte, 0]))
        parts.append(b'\xff\xff' * track_count)
        parts.append(b'\x00\x00\x00\x00')
    
    return b''.join(parts)


def update_container_metadata_for_song(song: Song) -> None:
    """
    Regenerate container metadata files to match the current track count.
    
    This should be called before writing a Song to GPX if tracks have been
    added or removed. It updates misc.xml, PartConfiguration, and
    LayoutConfiguration in format_extras.container_files.
    
    Note: This function regenerates metadata with default track visibility and
    layout settings. If the original file had custom display settings (e.g.,
    specific track ordering, visibility toggles, or layout preferences), those
    settings will be lost and replaced with defaults. For files where only
    the track count needs updating while preserving other display settings,
    a more sophisticated approach would be needed to parse and update the
    existing binary metadata rather than regenerating it from scratch.
    
    Args:
        song: Song with format_extras to update
    """
    if song.format_extras is None:
        return
    
    track_count = len(song.tracks)
    
    # Generate new metadata
    new_misc_xml = generate_misc_xml(track_count)
    new_part_config = generate_part_configuration(track_count)
    new_layout_config = generate_layout_configuration(track_count)
    
    replacements = {
        'misc.xml': new_misc_xml,
        'PartConfiguration': new_part_config,
        'LayoutConfiguration': new_layout_config,
    }
    
    # Replace or add the files
    container_files = []
    replaced = set()
    
    for name, content in song.format_extras.container_files:
        if name in replacements:
            container_files.append((name, replacements[name]))
            replaced.add(name)
        else:
            container_files.append((name, content))
    
    # Add any that weren't present
    for name, content in replacements.items():
        if name not in replaced:
            container_files.append((name, content))
    
    # Update the song's format_extras with new container_files tuple
    from .models import GpifExtras
    song.format_extras = GpifExtras(
        gp_version=song.format_extras.gp_version,
        gp_revision=song.format_extras.gp_revision,
        encoding_description=song.format_extras.encoding_description,
        automations=song.format_extras.automations,
        master_track_anacrusis=song.format_extras.master_track_anacrusis,
        track_rse_xml=song.format_extras.track_rse_xml,
        track_sounds_xml=song.format_extras.track_sounds_xml,
        track_automations_xml=song.format_extras.track_automations_xml,
        container_files=tuple(container_files),
    )
