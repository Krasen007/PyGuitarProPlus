# Voice Structure Fix: Empty Track Issue

## Problem

After implementing the container metadata fix, the second track was visible in Guitar Pro but appeared empty, even though Python parsing showed 699 notes.

## Root Cause

The `clone_measure()` function was **appending voices** to auto-created empty voices instead of **replacing** them.

### What Was Happening

1. `gp.Measure(track=target_track, header=target_header)` auto-creates empty voices (likely 2)
2. `clone_measure()` then appended source voices to `measure.voices`
3. Result: 6 voices total (2 empty + 4 from source), with notes in Voice 2 instead of Voice 0

```python
# Before fix:
Vocal Track (measure 2):   4 voices, notes in Voice 0 ✅
Arrangement Track (source): 4 voices, notes in Voice 0 ✅
Merged Track 2:             6 voices, notes in Voice 2 ❌  <-- WRONG!
```

### Why This Caused Empty Display

Guitar Pro displays notes from Voice 0 (and possibly Voice 1). With notes starting at Voice 2, the track appeared empty in the GUI even though the data was present.

## The Fix

Added one line to clear auto-created voices before cloning:

```python
def clone_measure(
    source: gp.Measure,
    target_track: gp.Track,
    target_header: gp.MeasureHeader,
) -> gp.Measure:
    """Deep-copy a measure into a target track and transpose its frets."""
    measure = gp.Measure(track=target_track, header=target_header)
    measure.lineBreak = source.lineBreak
    measure.voices = []  # ← NEW: Clear any auto-created voices

    for source_voice in source.voices:
        voice = gp.Voice(measure=measure)
        # ... rest of cloning logic
```

## Verification

### Before Fix
```
Track 2: Steel Guitar - 699 notes
  Measure 2: 6 voices
    Voice 0: 0 beats, 0 notes  ← Empty
    Voice 1: 0 beats, 0 notes  ← Empty
    Voice 2: 5 beats, 5 notes  ← Notes here, not visible in GP
    ...
```

### After Fix
```
Track 2: Steel Guitar - 699 notes
  Measure 2: 4 voices
    Voice 0: 5 beats, 5 notes  ← Notes here, visible in GP ✅
    Voice 1: 0 beats, 0 notes
    Voice 2: 0 beats, 0 notes
    Voice 3: 0 beats, 0 notes
```

## Impact

**Before**: Track visible in Guitar Pro but appeared completely empty  
**After**: Track visible and all 699 notes display correctly

## Related Issues

This was a **merge script bug**, not a library bug. The container metadata fix (earlier work) correctly made the track visible. This voice structure fix made the track actually display notes.

## Lessons Learned

1. `gp.Measure()` auto-creates empty voices when instantiated
2. Must clear `measure.voices = []` before manually populating
3. Voice 0 is the primary voice for display in Guitar Pro
4. Python parsing can show notes even when GUI doesn't display them
5. Always verify voice structure, not just note counts

## Files Modified

- `merge_in_and_out_v4_simplified.py`: Added `measure.voices = []` in `clone_measure()`

## Final Status

✅ Container metadata fix: Tracks visible in Guitar Pro  
✅ Voice structure fix: Notes display correctly in tracks  
✅ Both fixes combined: Complete working merge of vocal + arrangement

The v4 simplified.gpx file now has:
- Track 1: Nylon Guitar (vocal, 360 notes) - visible and playable
- Track 2: Steel Guitar (arrangement, 699 notes) - visible and playable
- All 99 measures with correct markers
- Correct container metadata (PreferredTrackCount=2)
- Proper voice structure (notes in Voice 0)
