# Guitar Pro 6 Container Metadata Fix

## Problem

The `guitarpro` Python library had a defect when writing GPX (Guitar Pro 6/7) files after modifying the track list:

- **Score XML correctly updated**: The GPIF writer properly updated `score.gpif` with current tracks
- **Container metadata not updated**: The writer blindly copied `misc.xml`, `PartConfiguration`, and `LayoutConfiguration` from the source file without updating them to match the new track count
- **Result**: Files with internally inconsistent metadata that Guitar Pro displayed incorrectly

### Example Failure Case

When adding a second track to a one-track GPX file:
- `score.gpif` correctly showed 2 tracks
- `misc.xml` still had `<PreferredTrackCount>1</PreferredTrackCount>`
- `PartConfiguration` and `LayoutConfiguration` were still the one-track binary data
- Guitar Pro opened the file but only displayed the first track

## Root Cause

In `src/guitarpro/gp6.py`, the `GP6File.writeSong()` method:
1. Generated fresh GPIF XML via `GpifWriter().write()` (correct)
2. Copied all `format_extras.container_files` unchanged from the source (bug)

There was no code to regenerate or update container metadata when tracks changed.

## Solution

### 1. New Module: `gp6_container_metadata.py`

Created `src/guitarpro/gp6_container_metadata.py` with functions to generate container metadata:

```python
def generate_misc_xml(track_count: int) -> bytes
def generate_part_configuration(track_count: int) -> bytes  
def generate_layout_configuration(track_count: int) -> bytes
def update_container_metadata_for_song(song: Song) -> None
```

The binary formats were reverse-engineered from Guitar Pro files:

#### `misc.xml` Structure
Simple XML with track count:
```xml
<?xml version="1.0" encoding="utf-8"?>
<MISC>
	<TracksView>
		<PreferredTrackCount>N</PreferredTrackCount>
	</TracksView>
</MISC>
```

#### `PartConfiguration` Structure
Big-endian binary format:
- 1 track (20 bytes): `00000002 00000000 01030000 00000103 00000001`
- 2 tracks (27 bytes): `00000003 00000000 02030100 00000001 03000000 00010100 000001`
- Pattern: First int32 = track_count + 1, followed by track-specific data

#### `LayoutConfiguration` Structure  
Big-endian binary format controlling GUI layout:
- 1 track (12 bytes): `00000004 0000ffff 00000000`
- 2 tracks (14 bytes): `00000004 0300ffff ffff0000 0000`
- Pattern: Starts with 0x00000004, then visibility markers

### 2. Modified `GP6File.writeSong()`

Updated `src/guitarpro/gp6.py` to call `update_container_metadata_for_song()` before writing:

```python
def writeSong(self, song: Song) -> None:
    """Write a GP6 (.gpx) file."""
    # Regenerate container metadata to match current track count
    update_container_metadata_for_song(song)
    
    gpif_bytes = GpifWriter().write(song, target_major_version=6)
    # ... rest of write logic
```

## Verification

### Test Results

**Test 1: Adding a track updates metadata**
- ✅ Loaded 1-track file with `PreferredTrackCount=1`
- ✅ Added second track programmatically  
- ✅ Written file had `PreferredTrackCount=2`
- ✅ `PartConfiguration` updated to 27 bytes (2-track format)
- ✅ `LayoutConfiguration` updated to 14 bytes (2-track format)

**Test 2: Simplified merge (no manual workaround needed)**
- ✅ Merged vocal + arrangement tracks without manual metadata copying
- ✅ Output file correctly showed 2 tracks in container metadata
- ✅ Both tracks visible when file is opened

**Test 3: Metadata comparison**
- ✅ `PartConfiguration`: byte-identical to manual workaround
- ✅ `LayoutConfiguration`: byte-identical to manual workaround  
- ✅ `misc.xml`: functionally identical (1 byte difference in trailing whitespace)

## Impact

### Before Fix
```python
# Users had to manually copy container metadata
main_song.format_extras = GpifExtras(
    # ... copy everything from a known-good source file
    container_files=copied_from_working_file
)
gp.write(main_song, path)
```

### After Fix
```python
# Just modify tracks and write - metadata updates automatically
main_song.tracks.append(new_track)
gp.write(main_song, path)
```

## Files Changed

1. **New**: `src/guitarpro/gp6_container_metadata.py` - Container metadata generation
2. **Modified**: `src/guitarpro/gp6.py` - Auto-update metadata on write
3. **Test**: `test_container_metadata_fix.py` - Comprehensive test suite
4. **Example**: `merge_in_and_out_v4_simplified.py` - Simplified merge without workarounds

## Remaining Work

### For 3+ Tracks
The binary format patterns for 3+ tracks are extrapolated from 1- and 2-track examples. While the patterns appear consistent, they should be verified against real 3+ track Guitar Pro files.

### For Track Removal
Tests currently cover adding tracks. Removing tracks should also be tested to ensure metadata updates correctly.

### For Guitar Pro 7
GP7 (.gp) files may have different container metadata. This fix is specific to GP6 (.gpx) format.

### Documentation
Consider adding this information to the library's main documentation and potentially a migration guide for users who have implemented manual workarounds.

## References

- Original issue: Container metadata copied unchanged from source file
- Files analyzed: `Armin van Buuren - In And Out Of Love` (ver 2 and ver 3)
- Parser verification: Tracks correctly loaded but GUI display incorrect
- Hash comparison: Confirmed byte-identical binary generation
