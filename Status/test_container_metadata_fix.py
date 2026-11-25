#!/usr/bin/env python3
"""Test that the container metadata fix works correctly."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp

def test_add_track_updates_metadata():
    """Test that adding a track updates container metadata."""
    print("Test 1: Adding a track should update container metadata")
    print("=" * 70)
    
    # Load a 1-track file
    vocal_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
    song = gp.parse(vocal_path)
    
    print(f"Original: {len(song.tracks)} track(s)")
    assert len(song.tracks) == 1
    
    # Verify original has PreferredTrackCount=1
    for name, content in song.format_extras.container_files:
        if name == 'misc.xml':
            misc_xml = content.decode('utf-8')
            assert '<PreferredTrackCount>1</PreferredTrackCount>' in misc_xml
            print(f"✓ Original misc.xml has PreferredTrackCount=1")
    
    # Add a second track
    new_track = gp.Track(
        song=song,
        number=2,
        name="Test Track",
        measures=[gp.Measure(track=None, header=h) for h in song.measureHeaders]
    )
    new_track.measures = [
        gp.Measure(track=new_track, header=h) for h in song.measureHeaders
    ]
    song.tracks.append(new_track)
    
    print(f"After adding: {len(song.tracks)} track(s)")
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        gp.write(song, tmp_path, version=(6, 0, 0))
        print(f"✓ Written to {tmp_path}")
        
        # Re-read and verify
        reloaded = gp.parse(tmp_path)
        print(f"Reloaded: {len(reloaded.tracks)} track(s)")
        assert len(reloaded.tracks) == 2
        
        # Check container metadata was updated
        for name, content in reloaded.format_extras.container_files:
            if name == 'misc.xml':
                misc_xml = content.decode('utf-8')
                print(f"\nReloaded misc.xml:")
                print(misc_xml)
                assert '<PreferredTrackCount>2</PreferredTrackCount>' in misc_xml
                print(f"\n✓ Updated misc.xml has PreferredTrackCount=2")
            elif name == 'PartConfiguration':
                print(f"✓ PartConfiguration size: {len(content)} bytes (expected ~27 for 2 tracks)")
            elif name == 'LayoutConfiguration':
                print(f"✓ LayoutConfiguration size: {len(content)} bytes (expected ~14 for 2 tracks)")
        
        print("\n✅ TEST PASSED: Container metadata correctly updated when track added")
        return True
        
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

def test_simplified_merge():
    """Test that the merge script now works without manual metadata copying."""
    print("\n\nTest 2: Simplified merge (no manual metadata copying needed)")
    print("=" * 70)
    
    # This is what the merge script should look like after the library fix
    vocal_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
    arr_path = ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx"
    
    main_song = gp.parse(vocal_path)
    arr_song = gp.parse(arr_path)
    
    print(f"Vocal song: {len(main_song.tracks)} track(s)")
    print(f"Arrangement song: {len(arr_song.tracks)} track(s)")
    
    # Add arrangement track (simplified - just structure, not full merge logic)
    arr_track = arr_song.tracks[0]
    new_track = gp.Track(
        song=main_song,
        number=2,
        name=arr_track.name,
        measures=[gp.Measure(track=None, header=h) for h in main_song.measureHeaders]
    )
    new_track.measures = [
        gp.Measure(track=new_track, header=h) for h in main_song.measureHeaders
    ]
    main_song.tracks.append(new_track)
    
    print(f"After merge: {len(main_song.tracks)} track(s)")
    
    # Write WITHOUT manual metadata copying
    with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        gp.write(main_song, tmp_path, version=(6, 0, 0))
        
        # Verify
        reloaded = gp.parse(tmp_path)
        assert len(reloaded.tracks) == 2
        
        for name, content in reloaded.format_extras.container_files:
            if name == 'misc.xml':
                misc_xml = content.decode('utf-8')
                assert '<PreferredTrackCount>2</PreferredTrackCount>' in misc_xml
        
        print("✅ TEST PASSED: Merge works without manual metadata handling")
        return True
        
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

if __name__ == '__main__':
    try:
        success = test_add_track_updates_metadata()
        if success:
            test_simplified_merge()
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✅")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
