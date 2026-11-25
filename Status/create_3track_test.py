#!/usr/bin/env python3
"""Create a 3-track GP6 file to test our metadata generation."""

import sys
import tempfile
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

# Load a 2-track file
print("Loading 2-track file...")
arr_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx"
song = gp.parse(arr_path)
print(f"Original: {len(song.tracks)} tracks")

# Add a third track
print("\nAdding a third track...")
new_track = gp.Track(
    song=song,
    number=3,
    name="Test Track 3",
    measures=[gp.Measure(track=None, header=h) for h in song.measureHeaders]
)
new_track.measures = [
    gp.Measure(track=new_track, header=h) for h in song.measureHeaders
]
song.tracks.append(new_track)
print(f"After adding: {len(song.tracks)} tracks")

# Write to temp file
output_path = ROOT / "Status" / "test_3tracks.gpx"
print(f"\nWriting to {output_path}...")
gp.write(song, output_path, version=(6, 0, 0))

# Re-read and inspect
print("\nReloading and inspecting metadata...")
reloaded = gp.parse(output_path)
print(f"Reloaded: {len(reloaded.tracks)} tracks")

for name, content in reloaded.format_extras.container_files:
    if name == 'misc.xml':
        print(f"\n{name}:")
        print(content.decode('utf-8'))
    elif name in ('PartConfiguration', 'LayoutConfiguration'):
        hex_dump(content, name)

print("\n✅ 3-track file created and inspected")
print(f"File saved at: {output_path}")
