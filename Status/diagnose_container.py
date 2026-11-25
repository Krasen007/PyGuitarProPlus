#!/usr/bin/env python3
"""Diagnose GPX container metadata files."""

import sys
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp

def show_container_files(path: Path, label: str):
    """Show relevant container file info."""
    print(f"\n{'='*60}")
    print(f"{label}: {path.name}")
    print('='*60)
    
    song = gp.parse(path)
    print(f"Tracks: {len(song.tracks)}")
    for t in song.tracks:
        print(f"  - Track {t.number}: {t.name}")
    
    if not song.format_extras:
        print("No format_extras")
        return
    
    for name, content in song.format_extras.container_files:
        if name in ('misc.xml', 'PartConfiguration', 'LayoutConfiguration'):
            print(f"\n--- {name} ---")
            if name == 'misc.xml':
                print(content.decode('utf-8', errors='replace')[:500])
            else:
                # Binary files - show size and first few bytes
                print(f"Size: {len(content)} bytes")
                print(f"First 80 bytes (hex): {content[:80].hex()}")

# Compare files
vocal_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
arr_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx"
v4_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 4).gpx"

show_container_files(vocal_path, "VOCAL (1 track)")
show_container_files(arr_path, "ARRANGEMENT (2 tracks)")
show_container_files(v4_path, "V4 OUTPUT (should be 2 tracks)")
