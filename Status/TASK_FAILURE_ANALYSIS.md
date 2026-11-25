# Why the v4 file failed to show the added guitar track

## Short answer

The note mapping was not the failure. The Python library is wrong/incomplete for this use case.

`guitarpro` correctly parses both source files, and its GPIF writer correctly puts the second track into `score.gpif`. But `GP6File.writeSong()` copies the original GPX container metadata unchanged from the parsed source song. Because the main/reference file had only one track, the written v4 file kept one-track container metadata.

That made the file internally inconsistent:

- `score.gpif`: two tracks, `Nylon Guitar` and `Steel Guitar`.
- `misc.xml`: still `<PreferredTrackCount>1</PreferredTrackCount>`.
- `PartConfiguration`: byte-identical to the one-track vocal source.
- `LayoutConfiguration`: the one-track layout from the vocal source.

Guitar Pro most likely reads those container files when deciding which parts/tracks to display. That explains why the file parsed as two tracks in Python but appeared to contain only the vocal track in Guitar Pro.

## Evidence collected before the fix

The first v4 file was checked with `guitarpro.parse()` and by unpacking the GPX container:

- Parsed tracks: `(1, 'Nylon Guitar', 99)` and `(2, 'Steel Guitar', 99)`.
- `score.gpif` contained two `<Track>` elements.
- `MasterTrack/Tracks` was `'0 1'`.
- There were 99 `MasterBar` elements and 198 `Bar` elements.
- All 198 bar references were valid; `-1` references: `0`.

So the writer did not drop the added track and did not leave the new track without bars.

The container metadata told a different story:

- v4 `misc.xml` was byte-identical to the one-track vocal source and contained `<PreferredTrackCount>1</PreferredTrackCount>`.
- v4 `PartConfiguration` SHA-256 prefix was `ad06fb810986971f`, identical to the one-track vocal source.
- The working two-track arrangement source had `<PreferredTrackCount>2</PreferredTrackCount>`.
- Its `PartConfiguration` SHA-256 prefix was `bc9f8c4dfbf2e08b`.
- Its `LayoutConfiguration` SHA-256 prefix was `6c11dede3e5e3071`, while the one-track source/v4 was `ab6b215701d54cba`.

## Why this is a library defect

The relevant library code is:

- `src/guitarpro/gp6.py:55-63`: `GP6File.writeSong()` calls `GpifWriter().write(...)`, writes `score.gpif`, then copies every `format_extras.container_files` entry from the source song unchanged.
- `src/guitarpro/gpif/gpif_writer.py:298-300`: the writer creates `<MasterTrack><Tracks>` from the current `song.tracks`.
- `src/guitarpro/gpif/gpif_writer.py:338`: the writer creates one `<Track>` element per current track.

The GPIF XML side follows the in-memory track list. The GPX container side does not. There is no code that regenerates or updates `misc.xml`, `PartConfiguration`, or `LayoutConfiguration` when tracks are added or removed.

Therefore, when a parsed one-track song is modified to have two tracks and then written as GPX, the library produces an internally inconsistent file. That is a real library bug/limitation, not a bad merge script.

## Fix applied

The temporary merge script was changed before the final write:

- File: `C:\Users\krase\AppData\Local\Temp\opencode\merge_in_and_out_v4.py`
- Added: copying `PartConfiguration`, `LayoutConfiguration`, and `misc.xml` from the two-track arrangement source into the output song's `format_extras.container_files`.

No library source code was changed.

`BinaryStylesheet` was left from the vocal source. Its strings are global style keys such as `Staff/*`, `System/*`, and `Global/Font/*`; no per-track count or visibility state was found in it.

## Final verification

The regenerated file is:

- Path: `F:\AI\repos\PyGuitarProPlus\Armin van Buuren - In And Out Of Love (ver 4).gpx`
- Size: `387085` bytes
- SHA-256: `23e7a0fcc3d9871ce2ce3a8bb2c93127bec723758ea6459329da330f9040a589`

Checks passed:

- `guitarpro.parse()` sees two tracks: `Nylon Guitar` with `360` notes and `Steel Guitar` with `699` notes.
- Version: `(6, 0, 0)`.
- Title: `Armin van Buuren feat. Sharon Den Adel`.
- Tempo: `135`.
- Measures: `99`.
- Markers: `(2, 'Intro')`, `(10, 'Verse')`, `(26, 'Chorus')`, `(76, 'Verse')`, `(92, 'Outro')`.
- `score.gpif`: `2` tracks, `99` master bars, `198` bars, `198` valid bar references, `0` missing references.
- Container metadata hashes match the two-track arrangement source.
- `misc.xml` has `<PreferredTrackCount>2</PreferredTrackCount>`.
- The 98 mapped measures matched the arrangement source with the intended +1 semitone transposition; mismatches: `0`.

## Remaining uncertainty

I did not open Guitar Pro itself here, so UI visibility is not independently verified. The file-level evidence strongly supports the container-metadata diagnosis, and the saved v4 now has matching score XML and container metadata.

If Guitar Pro still shows only one track, the next thing to test is copying all container files from a known two-track GPX source, including `BinaryStylesheet`, or patching `GP6File.writeSong()` so it regenerates container metadata whenever the track count changes.
