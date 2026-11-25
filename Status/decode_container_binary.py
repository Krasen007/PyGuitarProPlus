#!/usr/bin/env python3
"""Decode PartConfiguration and LayoutConfiguration binary structure."""

import struct
import sys
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp

def decode_bytes(data: bytes, label: str):
    """Try to decode binary data as integers."""
    print(f"\n{label} ({len(data)} bytes):")
    print(f"Hex: {data.hex()}")
    
    # Try as big-endian 32-bit integers
    if len(data) % 4 == 0:
        values = struct.unpack(f'>{len(data)//4}I', data)
        print(f"As big-endian int32s: {values}")
    
    # Try as little-endian 32-bit integers
    if len(data) % 4 == 0:
        values = struct.unpack(f'<{len(data)//4}I', data)
        print(f"As little-endian int32s: {values}")
    
    # Show byte-by-byte
    print(f"Bytes: {list(data)}")

def analyze_file(path: Path, label: str):
    """Analyze container files from a GPX."""
    print(f"\n{'='*70}")
    print(f"{label}: {path.name}")
    print('='*70)
    
    song = gp.parse(path)
    print(f"Track count: {len(song.tracks)}")
    
    if not song.format_extras:
        return
    
    for name, content in song.format_extras.container_files:
        if name == 'PartConfiguration':
            decode_bytes(content, "PartConfiguration")
        elif name == 'LayoutConfiguration':
            decode_bytes(content, "LayoutConfiguration")

# Test with 1-track, 2-track, and 3-track files if available
vocal_1 = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
arr_2 = ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx"

analyze_file(vocal_1, "1-TRACK FILE")
analyze_file(arr_2, "2-TRACK FILE")

# Try to find pattern
print("\n" + "="*70)
print("PATTERN ANALYSIS")
print("="*70)
print("""
Looking at the data:

1-track PartConfiguration (20 bytes):
  00000002 00000000 01030000 00000103 00000001

2-track PartConfiguration (27 bytes):
  00000003 00000000 02030100 00000001 03000000 00010100 000001

1-track LayoutConfiguration (12 bytes):
  00000004 0000ffff 00000000

2-track LayoutConfiguration (14 bytes):
  00000004 0300ffff ffff0000 0000

Hypothesis:
- PartConfiguration: starts with count+1 (2 for 1 track, 3 for 2 tracks)
- LayoutConfiguration: may encode visible track indexes
- Both appear to be big-endian integers
""")
