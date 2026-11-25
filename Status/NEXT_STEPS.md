# Next Steps: Container Metadata Fix

## Summary

Fixed the PyGuitarPro library defect where GPX files written after modifying tracks had stale container metadata causing Guitar Pro to display the wrong number of tracks.

**Status**: ✅ Core fix complete and tested  
**Location**: `src/guitarpro/gp6_container_metadata.py` + updated `src/guitarpro/gp6.py`

## Immediate Next Steps

### 1. Test with Guitar Pro Application
**Priority**: HIGH  
**Action**: Open the generated files in actual Guitar Pro 6/7 to visually confirm both tracks are visible

```bash
# Test these files in Guitar Pro:
F:\AI\repos\PyGuitarProPlus\Armin van Buuren - In And Out Of Love (ver 4).gpx
F:\AI\repos\PyGuitarProPlus\Armin van Buuren - In And Out Of Love (ver 4 simplified).gpx
```

**Expected**: Both files should show Nylon Guitar (vocal) and Steel Guitar (arrangement) tracks side-by-side

**If it fails**: The binary format patterns may need adjustment (see section below)

### 2. Test Track Removal
**Priority**: MEDIUM  
**Action**: Test that removing tracks also updates metadata correctly

```python
# Test case to add:
song = gp.parse(two_track_file)
del song.tracks[1]
gp.write(song, output_path)
reloaded = gp.parse(output_path)
# Should have 1 track with PreferredTrackCount=1
```

### 3. Test with 3+ Tracks
**Priority**: MEDIUM  
**Action**: Find or create a 3+ track GPX file and verify the extrapolated binary patterns

The current implementation extrapolates patterns from 1- and 2-track examples. For N ≥ 3 tracks:
- `PartConfiguration`: First int32 = N+1, then track-specific segments
- `LayoutConfiguration`: Marker byte = (N*2)-3, then N `0xffff` pairs

This should be validated against real Guitar Pro files.

### 4. Consider Edge Cases

**Empty song** (0 tracks):
- Currently generates minimal metadata
- May need testing with actual Guitar Pro behavior

**Track reordering**:
- If tracks are reordered, does metadata need to encode the new order?
- Current implementation assumes tracks are sequential

**Hidden/muted tracks**:
- Does metadata encode per-track visibility state?
- Current implementation treats all added tracks as visible

## Integration Options

### Option A: Keep as Automatic (Recommended)
Current implementation: `writeSong()` always regenerates metadata before writing.

**Pros**:
- Zero user burden
- Impossible to create inconsistent files
- Matches user expectations

**Cons**:
- Slight performance overhead (negligible)
- May overwrite custom metadata users set (rare)

### Option B: Opt-in Regeneration
Add a parameter: `gp.write(song, path, update_metadata=True)`

**Pros**:
- Explicit control
- Preserves any custom metadata

**Cons**:
- Users will forget to set it and files will break
- Requires documentation and migration

**Recommendation**: Stick with Option A unless users report issues

## Code Quality Improvements

### 1. Add Unit Tests to Library
Move `test_container_metadata_fix.py` into the library's test suite:
```
tests/
  test_gp6_container_metadata.py  # New
```

### 2. Add Docstring Examples
```python
def update_container_metadata_for_song(song: Song) -> None:
    """
    Regenerate container metadata to match current track count.
    
    Example:
        >>> song = gp.parse('one_track.gpx')
        >>> song.tracks.append(new_track)
        >>> gp.write(song, 'two_tracks.gpx')  # Metadata auto-updated
    """
```

### 3. Add Logging
```python
import logging
logger = logging.getLogger(__name__)

def update_container_metadata_for_song(song: Song) -> None:
    if song.format_extras is None:
        return
    
    track_count = len(song.tracks)
    logger.debug(f"Regenerating GPX container metadata for {track_count} tracks")
    # ... rest of function
```

### 4. Add Format Validation
```python
def validate_container_metadata(song: Song) -> bool:
    """Check if container metadata matches track count."""
    if not song.format_extras:
        return True
    
    for name, content in song.format_extras.container_files:
        if name == 'misc.xml':
            match = re.search(rb'<PreferredTrackCount>(\d+)</PreferredTrackCount>', content)
            if match and int(match.group(1)) != len(song.tracks):
                return False
    return True
```

## Documentation Needs

### 1. Update Library README
Add section: "Track Manipulation" explaining that container metadata is automatically managed.

### 2. Migration Guide
For users who implemented manual workarounds:

> **Before (manual workaround needed):**
> ```python
> # Copy metadata from a working two-track file
> copy_two_track_container_metadata(main_song, reference_song)
> gp.write(main_song, output_path)
> ```
>
> **After (automatic, no workaround needed):**
> ```python
> # Just write - metadata updates automatically
> gp.write(main_song, output_path)
> ```

### 3. Add to Changelog
```markdown
## [Unreleased]
### Fixed
- GPX container metadata now automatically updates when tracks are added or removed
- Files written after track modifications now display correctly in Guitar Pro
- No manual metadata copying required when merging or splitting tracks
```

## Potential Issues to Watch

### 1. Performance
Regenerating metadata on every write adds overhead. If writing many files in a loop, users may want to benchmark.

**Mitigation**: Only regenerate if track count changed since read.

### 2. Custom Metadata Loss
If users have customized `PartConfiguration` or `LayoutConfiguration` for special purposes, regeneration will overwrite it.

**Mitigation**: Document this behavior and provide a way to disable auto-regeneration if needed.

### 3. GP7 Format Differences
Guitar Pro 7 uses `.gp` files. The container structure may differ.

**Action**: Test with GP7 files and extend fix if needed.

## Success Criteria

The fix is complete when:

- [x] Library automatically updates metadata on write
- [x] Python tests pass (add tracks scenario)
- [ ] Guitar Pro app correctly displays files with added tracks
- [ ] Guitar Pro app correctly displays files with removed tracks
- [ ] 3+ track files tested and working
- [ ] Integration tests added to library test suite
- [ ] Documentation updated with examples
- [ ] Changelog entry added

## If Guitar Pro Still Shows Wrong Track Count

If the generated files still display incorrectly in Guitar Pro:

### Diagnostic Steps

1. **Extract and compare all container files**:
```python
# Compare every file in the working vs broken GPX
working_files = dict(working_song.format_extras.container_files)
broken_files = dict(broken_song.format_extras.container_files)
for name in working_files:
    if name in broken_files:
        if working_files[name] != broken_files[name]:
            print(f"Differs: {name}")
```

2. **Check BinaryStylesheet**:
The current fix doesn't touch `BinaryStylesheet`. If track visibility is encoded there, we may need to regenerate it too.

3. **Examine all XML files**:
```bash
# Extract GPX and check all XML files
for file in *.xml; do
    echo "=== $file ==="
    cat $file | grep -i track
done
```

4. **Compare with GP-generated files**:
Create a 2-track file in Guitar Pro, export, and compare byte-for-byte with our generated files.

5. **Check undocumented metadata**:
There may be additional metadata fields in GPIF XML that control track visibility that the parser doesn't expose.

## Final Recommendation

**Immediate action**: Test the generated files in Guitar Pro and report results. If they work, integrate the fix into the main library with tests and documentation. If they don't work, run the diagnostic steps above to identify missing metadata.

The core fix is sound and produces byte-identical binary metadata to the manual workaround, so if that workaround worked, this should too.
