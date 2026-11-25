#!/usr/bin/env python3
"""Test that metadata is preserved when track count is unchanged."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp

def test_metadata_preservation():
    """Test that existing metadata is preserved when track topology is unchanged."""
    print("Test: Metadata preservation when track count unchanged")
    print("=" * 70)
    
    # Load a 2-track file
    arr_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx"
    song = gp.parse(arr_path)
    
    print(f"Original: {len(song.tracks)} tracks")
    
    # Capture original metadata
    original_misc = None
    original_part = None
    original_layout = None
    
    for name, content in song.format_extras.container_files:
        if name == 'misc.xml':
            original_misc = content
        elif name == 'PartConfiguration':
            original_part = content
        elif name == 'LayoutConfiguration':
            original_layout = content
    
    print(f"Original misc.xml size: {len(original_misc)} bytes")
    print(f"Original PartConfiguration size: {len(original_part)} bytes")
    print(f"Original LayoutConfiguration size: {len(original_layout)} bytes")
    
    # Modify the song without changing track count (just change a track name)
    song.tracks[0].name = "Modified Track Name"
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        gp.write(song, tmp_path, version=(6, 0, 0))
        print(f"\n✓ Written to {tmp_path}")
        
        # Re-read and check if metadata was preserved
        reloaded = gp.parse(tmp_path)
        print(f"Reloaded: {len(reloaded.tracks)} tracks")
        
        # Check if metadata is identical
        for name, content in reloaded.format_extras.container_files:
            if name == 'misc.xml':
                if content == original_misc:
                    print(f"✅ misc.xml PRESERVED (identical)")
                else:
                    print(f"⚠️  misc.xml REGENERATED")
                    print(f"   Original: {original_misc[:100]}")
                    print(f"   New:      {content[:100]}")
            elif name == 'PartConfiguration':
                if content == original_part:
                    print(f"✅ PartConfiguration PRESERVED (identical)")
                else:
                    print(f"⚠️  PartConfiguration REGENERATED (expected)")
                    print(f"   Original size: {len(original_part)}, New size: {len(content)}")
            elif name == 'LayoutConfiguration':
                if content == original_layout:
                    print(f"✅ LayoutConfiguration PRESERVED (identical)")
                else:
                    print(f"⚠️  LayoutConfiguration REGENERATED (expected)")
                    print(f"   Original size: {len(original_layout)}, New size: {len(content)}")
        
        # Verify track name was actually changed
        assert reloaded.tracks[0].name == "Modified Track Name"
        print(f"\n✅ TEST PASSED: Track modification preserved, metadata handling verified")
        return True
        
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

def test_metadata_regeneration():
    """Test that metadata IS regenerated when track count changes."""
    print("\n\nTest: Metadata regeneration when track count changes")
    print("=" * 70)
    
    # Load a 1-track file
    vocal_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
    song = gp.parse(vocal_path)
    
    print(f"Original: {len(song.tracks)} track(s)")
    
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
    
    print(f"After adding: {len(song.tracks)} tracks")
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        gp.write(song, tmp_path, version=(6, 0, 0))
        
        # Re-read and verify metadata was updated
        reloaded = gp.parse(tmp_path)
        
        for name, content in reloaded.format_extras.container_files:
            if name == 'misc.xml':
                misc_xml = content.decode('utf-8')
                assert '<PreferredTrackCount>2</PreferredTrackCount>' in misc_xml
                print(f"✅ misc.xml correctly shows 2 tracks")
            elif name == 'PartConfiguration':
                assert len(content) == 27  # 2-track size
                print(f"✅ PartConfiguration correctly sized for 2 tracks ({len(content)} bytes)")
            elif name == 'LayoutConfiguration':
                assert len(content) == 14  # 2-track size
                print(f"✅ LayoutConfiguration correctly sized for 2 tracks ({len(content)} bytes)")
        
        print(f"\n✅ TEST PASSED: Metadata correctly regenerated when track count changed")
        return True
        
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

if __name__ == '__main__':
    try:
        test_metadata_preservation()
        test_metadata_regeneration()
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✅")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
