# Solution Summary: GPX Container Metadata Fix

## The Problem

When using the PyGuitarPro library to add or remove tracks from a Guitar Pro 6 (.gpx) file, the written file had **internally inconsistent metadata**:

- ✅ `score.gpif` XML correctly showed all tracks
- ❌ `misc.xml` had wrong `PreferredTrackCount`  
- ❌ `PartConfiguration` binary had wrong track count
- ❌ `LayoutConfiguration` binary had wrong layout data

**Result**: Guitar Pro opened the file but only displayed some of the tracks.

## The Root Cause

In `src/guitarpro/gp6.py`, the `GP6File.writeSong()` method:
1. ✅ Generated fresh GPIF XML with current tracks
2. ❌ Copied all container files unchanged from the source file

There was **no code to regenerate container metadata** when tracks changed.

## The Solution

### Created: `src/guitarpro/gp6_container_metadata.py`

New module with functions to generate correct container metadata:

```python
def generate_misc_xml(track_count: int) -> bytes
    """Generate misc.xml with correct PreferredTrackCount."""

def generate_part_configuration(track_count: int) -> bytes
    """Generate PartConfiguration binary (track visibility/ordering)."""

def generate_layout_configuration(track_count: int) -> bytes
    """Generate LayoutConfiguration binary (GUI layout)."""

def update_container_metadata_for_song(song: Song) -> None
    """Regenerate all three files to match current track count."""
```

Binary formats were **reverse-engineered** from Guitar Pro files:

| Tracks | misc.xml | PartConfiguration | LayoutConfiguration |
|--------|----------|-------------------|---------------------|
| 1      | PreferredTrackCount=1 | 20 bytes | 12 bytes |
| 2      | PreferredTrackCount=2 | 27 bytes | 14 bytes |
| 3+     | PreferredTrackCount=N | ~7N bytes | ~2N+6 bytes |

### Modified: `src/guitarpro/gp6.py`

Updated `GP6File.writeSong()` to auto-update metadata:

```python
def writeSong(self, song: Song) -> None:
    """Write a GP6 (.gpx) file."""
    update_container_metadata_for_song(song)  # ← NEW: Auto-fix metadata
    
    gpif_bytes = GpifWriter().write(song, target_major_version=6)
    # ... rest of write logic
```

## Impact on Users

### Before the Fix

```python
# Users had to manually copy metadata from a reference file
main_song = gp.parse('one_track.gpx')
reference_song = gp.parse('known_good_two_track.gpx')

# Manual workaround - error-prone and confusing
extras = main_song.format_extras
ref_extras = reference_song.format_extras
ref_files = dict(ref_extras.container_files)
container_files = tuple(
    (name, ref_files.get(name, content) if name in ('misc.xml', 'PartConfiguration', 'LayoutConfiguration') else content)
    for name, content in extras.container_files
)
main_song.format_extras = GpifExtras(
    gp_version=extras.gp_version,
    # ... copy all 8 fields manually
    container_files=container_files,
)

main_song.tracks.append(new_track)
gp.write(main_song, 'two_track.gpx')
```

### After the Fix

```python
# Just modify tracks and write - that's it!
main_song = gp.parse('one_track.gpx')
main_song.tracks.append(new_track)
gp.write(main_song, 'two_track.gpx')  # ← Metadata auto-updated
```

**90% less code, zero manual metadata handling.**

## Verification Results

### Test 1: Add Track to 1-Track File
```
✅ Loaded 1-track file
✅ Added second track programmatically
✅ Written file has PreferredTrackCount=2
✅ PartConfiguration: 27 bytes (2-track format)
✅ LayoutConfiguration: 14 bytes (2-track format)
✅ Re-parsed file shows 2 tracks correctly
```

### Test 2: Simplified Merge Script
```
✅ Merged vocal (1 track) + arrangement (2 tracks)
✅ No manual metadata copying needed
✅ Output has 2 tracks with correct metadata
✅ All container files properly formatted
```

### Test 3: Metadata Comparison
```
✅ PartConfiguration: byte-identical to manual workaround
✅ LayoutConfiguration: byte-identical to manual workaround
✅ misc.xml: functionally identical (trailing whitespace differs)
```

## Files Modified

| File | Status | Purpose |
|------|--------|---------|
| `src/guitarpro/gp6_container_metadata.py` | **NEW** | Generate container metadata |
| `src/guitarpro/gp6.py` | **MODIFIED** | Auto-update metadata on write |
| `test_container_metadata_fix.py` | **NEW** | Test suite |
| `merge_in_and_out_v4_simplified.py` | **NEW** | Example without workarounds |
| `CONTAINER_METADATA_FIX.md` | **NEW** | Technical documentation |
| `NEXT_STEPS.md` | **NEW** | Integration roadmap |

## Example: Before and After

### Scenario: Merge two GPX files

**Before (required workaround):**
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp
from guitarpro.models import GpifExtras

def copy_two_track_container_metadata(main_song, arrangement_song):
    """Manual workaround - copy metadata from 2-track reference."""
    extras = main_song.format_extras
    source_extras = arrangement_song.format_extras
    wanted = ('PartConfiguration', 'LayoutConfiguration', 'misc.xml')
    source_files = dict(source_extras.container_files)
    replacements = {name: source_files[name] for name in wanted}
    container_files = tuple(
        (name, replacements.get(name, content)) 
        for name, content in extras.container_files
    )
    main_song.format_extras = GpifExtras(
        gp_version=extras.gp_version,
        gp_revision=extras.gp_revision,
        encoding_description=extras.encoding_description,
        automations=extras.automations,
        master_track_anacrusis=extras.master_track_anacrusis,
        track_rse_xml=extras.track_rse_xml,
        track_sounds_xml=extras.track_sounds_xml,
        track_automations_xml=extras.track_automations_xml,
        container_files=container_files,
    )

main_song = gp.parse('vocal.gpx')
arr_song = gp.parse('arrangement.gpx')
main_song.tracks.append(arr_song.tracks[0])

# REQUIRED: Manual metadata copying
copy_two_track_container_metadata(main_song, arr_song)

gp.write(main_song, 'merged.gpx')
```

**After (automatic):**
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))
import guitarpro as gp

main_song = gp.parse('vocal.gpx')
arr_song = gp.parse('arrangement.gpx')
main_song.tracks.append(arr_song.tracks[0])

# That's it - metadata auto-updates!
gp.write(main_song, 'merged.gpx')
```

## Technical Details

### Container Metadata Files

**`misc.xml`**: Simple XML with track count
```xml
<?xml version="1.0" encoding="utf-8"?>
<MISC>
	<TracksView>
		<PreferredTrackCount>2</PreferredTrackCount>
	</TracksView>
</MISC>
```

**`PartConfiguration`**: Big-endian binary
- Structure: `int32(track_count+1) | zero_padding | per_track_data`
- 1 track: 20 bytes starting with `0x00000002`
- 2 tracks: 27 bytes starting with `0x00000003`

**`LayoutConfiguration`**: Big-endian binary
- Structure: `0x00000004 | marker_byte | visibility_flags | zero_padding`
- 1 track: 12 bytes with marker `0x00`
- 2 tracks: 14 bytes with marker `0x03`

### Design Decisions

1. **Automatic by default**: No opt-in flag needed
   - Pro: Can't forget and create broken files
   - Con: Minimal performance overhead
   
2. **Called from writeSong()**: Updates happen transparently
   - Pro: Works for all write paths
   - Con: May surprise users who customized metadata
   
3. **Preserves other container files**: Only updates the three metadata files
   - Pro: Doesn't break other GPX features
   - Con: Assumes other files aren't track-count-dependent

## Known Limitations

1. **3+ tracks**: Binary patterns are extrapolated, not tested against real GP files
2. **Track removal**: Not explicitly tested (but should work)
3. **GP7 format**: Only tested with GP6 (.gpx), GP7 (.gp) may differ
4. **Custom metadata**: Regeneration overwrites any custom edits users made

## Success Metrics

- [x] Library automatically updates metadata
- [x] Python tests pass for adding tracks
- [x] Generated metadata byte-identical to manual workaround
- [ ] Guitar Pro application displays files correctly *(needs manual testing)*
- [ ] Remove track scenario tested
- [ ] 3+ track files tested
- [ ] Integration tests added to library
- [ ] Documentation updated

## Next Action

**Open the generated GPX file in Guitar Pro 6 or 7 and verify both tracks are visible.**

Test file location:
```
F:\AI\repos\PyGuitarProPlus\Armin van Buuren - In And Out Of Love (ver 4 simplified).gpx
```

Expected result: 
- Track 1: Nylon Guitar (vocal, 360 notes)
- Track 2: Steel Guitar (arrangement, 699 notes)
- Both tracks should be visible and playable side-by-side

If this works, the fix is complete and ready to integrate into the library with tests and documentation.

## Credits

**Problem identified**: Container metadata not updated when tracks change  
**Root cause**: `GP6File.writeSong()` blindly copied metadata from source  
**Solution**: Auto-regenerate metadata on write  
**Implementation**: 220 lines of container metadata generation + 3-line fix to writer  
**Testing**: 100+ line test suite, verified byte-identical to manual workaround
