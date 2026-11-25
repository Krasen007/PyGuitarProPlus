#!/usr/bin/env python3
"""Try to decode the PartConfiguration structure more systematically."""

import struct

def decode_part_config(data: bytes, description: str):
    """Try to decode PartConfiguration structure."""
    print(f"\n{description} ({len(data)} bytes)")
    print("=" * 70)
    
    # Hex dump
    hex_str = ' '.join(f'{b:02x}' for b in data)
    print(f"Hex: {hex_str}")
    
    # Header
    header_size = struct.unpack('>I', data[0:4])[0]
    zero_pad = struct.unpack('>I', data[4:8])[0]
    print(f"\nHeader:")
    print(f"  [0-3]: {header_size} (track_count + 1)")
    print(f"  [4-7]: {zero_pad} (padding)")
    
    pos = 8
    print(f"\nAfter header (pos={pos}):")
    
    # Try to parse remaining as segments
    segment_num = 0
    while pos < len(data):
        # Try to read a segment
        if pos + 6 <= len(data):
            # Check if this looks like a 6-byte segment
            byte_vals = data[pos:pos+6]
            print(f"  Segment {segment_num} [{pos:2d}-{pos+5:2d}]: {' '.join(f'{b:02x}' for b in byte_vals)}")
            
            # Try to interpret first byte as count
            if byte_vals[0] > 0 and byte_vals[0] <= 10:
                print(f"    -> Possible count: {byte_vals[0]}")
            if byte_vals[1] == 0x03:
                print(f"    -> Contains 0x03 marker")
            if byte_vals[1] == 0x01:
                print(f"    -> Contains 0x01 marker")
                
            pos += 6
            segment_num += 1
        elif pos + 1 <= len(data):
            # Remaining bytes
            remaining = data[pos:]
            print(f"  Tail [{pos}:]: {' '.join(f'{b:02x}' for b in remaining)}")
            break
        else:
            break

# Known good patterns
pc1 = bytes.fromhex('00 00 00 02 00 00 00 00 01 03 00 00 00 00 01 03 00 00 00 01'.replace(' ', ''))
pc2 = bytes.fromhex('00 00 00 03 00 00 00 00 02 03 01 00 00 00 00 01 03 00 00 00 00 01 01 00 00 00 01'.replace(' ', ''))

decode_part_config(pc1, "1 Track (known good)")
decode_part_config(pc2, "2 Tracks (known good)")

# Try to understand the pattern
print("\n\n" + "="*70)
print("PATTERN ANALYSIS")
print("="*70)

print("\n1 Track structure:")
print("  00000002 00000000  = header (track_count+1=2, padding)")
print("  01 03 00 00 00 00  = 6 bytes")
print("  01 03 00 00 00 01  = 6 bytes")
print("  Total: 8 + 6 + 6 = 20 bytes")

print("\n2 Tracks structure:")
print("  00000003 00000000      = header (track_count+1=3, padding)")
print("  02 03 01 00 00 00 00   = 7 bytes")
print("  01 03 00 00 00 00      = 6 bytes")
print("  01 01 00 00 00 01      = 6 bytes")
print("  Total: 8 + 7 + 6 + 6 = 27 bytes")

print("\n3 Tracks structure (extrapolated):")
print("  00000004 00000000      = header (track_count+1=4, padding)")
print("  03 03 02 01 00 00 00   = 7 bytes (track indices)")
print("  01 03 00 00 00 00      = 6 bytes (view 0)")
print("  01 01 00 00 00 01      = 6 bytes (view 1)")
print("  01 01 00 00 00 01      = 6 bytes (view 2)")
print("  Total: 8 + 7 + 6 + 6 + 6 = 33 bytes")

print("\nNotice:")
print("  - Track indices section: starts with track_count, then 0x03, then descending")
print("  - For 1 track: no separate indices section (goes straight to views)")
print("  - For 2+ tracks: indices section is variable length")
print("  - Each view: 6 bytes starting with 0x01")
print("  - First view: 01 03 00 00 00 00")
print("  - Other views: 01 01 00 00 00 01")

print("\n\nHypothesis: Maybe the structure is:")
print("  Header: track_count+1, padding")
print("  For track_count >= 2:")
print("    - Track indices: variable length based on pattern")
print("  Views: (track_count) * 6 bytes")
print("    - First view: 01 03 00 00 00 00")
print("    - Others: 01 01 00 00 00 01")
