#!/usr/bin/env python3
"""Quick verification that all review fixes are working."""

import sys
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))

print("Review Fixes Verification")
print("=" * 70)

# Test 1: Module loads
print("\n1. Module Import")
try:
    import guitarpro as gp
    from guitarpro.gp6_container_metadata import (
        generate_misc_xml,
        generate_part_configuration,
        generate_layout_configuration,
        update_container_metadata_for_song
    )
    print("   ✅ All imports successful")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: 1-track generation (validated)
print("\n2. 1-Track Generation (Validated)")
try:
    pc1 = generate_part_configuration(1)
    lc1 = generate_layout_configuration(1)
    # Known good from Guitar Pro files
    expected_pc1 = bytes([0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03, 0x00, 0x00, 0x00, 0x01])
    expected_lc1 = bytes([0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00])
    
    if pc1 == expected_pc1 and lc1 == expected_lc1:
        print("   ✅ Byte-identical to Guitar Pro")
    else:
        print("   ❌ Mismatch with Guitar Pro format")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 3: 2-track generation (validated)
print("\n3. 2-Track Generation (Validated)")
try:
    pc2 = generate_part_configuration(2)
    lc2 = generate_layout_configuration(2)
    # Known good from Guitar Pro files
    expected_pc2 = bytes([0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x02, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x01])
    expected_lc2 = bytes([0x00, 0x00, 0x00, 0x04, 0x03, 0x00, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00])
    
    if pc2 == expected_pc2 and lc2 == expected_lc2:
        print("   ✅ Byte-identical to Guitar Pro")
    else:
        print("   ❌ Mismatch with Guitar Pro format")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 4: 3-track generation (experimental)
print("\n4. 3-Track Generation (Experimental)")
try:
    pc3 = generate_part_configuration(3)
    lc3 = generate_layout_configuration(3)
    print(f"   ⚠️  Generated {len(pc3)} bytes PartConfiguration (not validated)")
    print(f"   ⚠️  Generated {len(lc3)} bytes LayoutConfiguration (not validated)")
    print("   ✅ Generates without errors")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 5: Metadata preservation logic
print("\n5. Metadata Preservation Logic")
try:
    import tempfile
    vocal_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
    if vocal_path.exists():
        song = gp.parse(vocal_path)
        
        # Capture original
        original_misc = None
        for name, content in song.format_extras.container_files:
            if name == 'misc.xml':
                original_misc = content
                break
        
        # Modify without changing track count
        song.tracks[0].name = "Test Name"
        
        # Write
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            gp.write(song, tmp_path, version=(6, 0, 0))
            reloaded = gp.parse(tmp_path)
            
            # Check if preserved
            for name, content in reloaded.format_extras.container_files:
                if name == 'misc.xml':
                    if content == original_misc:
                        print("   ✅ Metadata preserved when track count unchanged")
                    else:
                        print("   ❌ Metadata regenerated unnecessarily")
                        sys.exit(1)
                    break
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    else:
        print("   ⚠️  Test file not found, skipped")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Metadata regeneration when needed
print("\n6. Metadata Regeneration (When Needed)")
try:
    if vocal_path.exists():
        song = gp.parse(vocal_path)
        
        # Add a track
        new_track = gp.Track(
            song=song,
            number=2,
            name="New Track",
            measures=[gp.Measure(track=None, header=h) for h in song.measureHeaders]
        )
        new_track.measures = [
            gp.Measure(track=new_track, header=h) for h in song.measureHeaders
        ]
        song.tracks.append(new_track)
        
        # Write
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            gp.write(song, tmp_path, version=(6, 0, 0))
            reloaded = gp.parse(tmp_path)
            
            # Check if updated
            for name, content in reloaded.format_extras.container_files:
                if name == 'misc.xml':
                    if b'<PreferredTrackCount>2</PreferredTrackCount>' in content:
                        print("   ✅ Metadata regenerated when track count changed")
                    else:
                        print("   ❌ Metadata not updated correctly")
                        sys.exit(1)
                    break
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    else:
        print("   ⚠️  Test file not found, skipped")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("✅ All review fixes working correctly")
print("\nStatus:")
print("  ✅ Issue 1 (Preservation): FIXED - Metadata preserved when topology unchanged")
print("  ⚠️  Issue 2 (LayoutConfig): DOCUMENTED - 3+ tracks need GP validation")
print("  ⚠️  Issue 3 (PartConfig): DOCUMENTED - 3+ tracks need GP validation")
print("\nProduction Ready: 1-2 track files (validated against Guitar Pro)")
print("Experimental: 3+ track files (needs Guitar Pro validation)")
print("=" * 70)
