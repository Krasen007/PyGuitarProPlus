#!/usr/bin/env python3
"""Inspect container metadata from real GP6 files to validate our format."""

import sys
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp

def hex_dump(data: bytes, name: str):
    """Print hex dump of binary data."""
    print(f"\n{name} ({len(data)} bytes):")
    print("=" * 70)
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"{i:04x}: {hex_str:<48} {ascii_str}")

def inspect_file(path: Path):
    """Inspect a GP6 file's container metadata."""
    print(f"\n{'='*70}")
    print(f"File: {path.name}")
    print(f"{'='*70}")
    
    song = gp.parse(path)
    print(f"Tracks: {len(song.tracks)}")
    for i, track in enumerate(song.tracks):
        print(f"  {i+1}. {track.name}")
    
    if song.format_extras:
        for name, content in song.format_extras.container_files:
            if name == 'misc.xml':
                print(f"\n{name}:")
                print(content.decode('utf-8'))
            elif name in ('PartConfiguration', 'LayoutConfiguration'):
                hex_dump(content, name)

if __name__ == '__main__':
    # Inspect files with different track counts
    files = [
        ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx",  # 1 track
        ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx",  # multiple tracks
    ]
    
    for file_path in files:
        if file_path.exists():
            inspect_file(file_path)
        else:
            print(f"File not found: {file_path}")
