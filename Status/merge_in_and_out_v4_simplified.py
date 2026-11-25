#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "attrs>=19.2",
# ]
# ///
# ─── How to run ───
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run merge_in_and_out_v4_simplified.py
# ──────────────────

"""
Merge full vocal track with arrangement tracks - SIMPLIFIED VERSION.

This version uses the library's automatic container metadata generation
instead of manually copying PartConfiguration/LayoutConfiguration files.

The library now automatically updates misc.xml, PartConfiguration, and
LayoutConfiguration when writing GPX files, so tracks added or removed
from a Song are correctly reflected in the output file.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(r"F:\AI\repos\PyGuitarProPlus")
sys.path.insert(0, str(ROOT / "src"))

import guitarpro as gp  # noqa: E402

VOCAL_PATH = ROOT / "Armin van Buuren - In And Out Of Love (ver 3 by Adrimor) full vocal only.gpx"
ARRANGEMENT_PATH = ROOT / "Armin van Buuren - In And Out Of Love (ver 2) not full.gpx"
OUTPUT_PATH = ROOT / "Armin van Buuren - In And Out Of Love (ver 4 simplified).gpx"

TRANSPOSE_SEMITONES = 1


def build_measure_map() -> dict[int, int]:
    """Map each target measure to its source arrangement measure."""
    result: dict[int, int] = {}

    def assign(start: int, sources: list[int]) -> None:
        for offset, source in enumerate(sources):
            target = start + offset
            if target in result:
                raise gp.GPException(f"duplicate target measure {target}")
            result[target] = source

    # Main score sections
    assign(2, list(range(1, 9)))  # Intro
    assign(10, list(range(9, 25)))  # Verse
    assign(26, (list(range(25, 49)) * 3)[:50])  # Chorus (repeated)
    assign(76, list(range(9, 25)))  # Verse
    assign(92, list(range(49, 57)))  # Outro

    expected = list(range(2, 100))
    if sorted(result) != expected:
        raise gp.GPException("measure map does not cover measures 2-99 exactly")
    return result


def clone_measure(
    source: gp.Measure,
    target_track: gp.Track,
    target_header: gp.MeasureHeader,
) -> gp.Measure:
    """Deep-copy a measure into a target track and transpose its frets."""
    measure = gp.Measure(track=target_track, header=target_header)
    measure.lineBreak = source.lineBreak
    measure.voices = []  # Clear any auto-created voices

    for source_voice in source.voices:
        voice = gp.Voice(measure=measure)
        voice.direction = source_voice.direction

        for source_beat in source_voice.beats:
            beat = gp.Beat(voice=voice)
            beat.duration = copy.deepcopy(source_beat.duration)
            beat.text = source_beat.text
            beat.effect = copy.deepcopy(source_beat.effect)
            beat.octave = source_beat.octave
            beat.display = copy.deepcopy(source_beat.display)
            beat.status = source_beat.status

            for source_note in source_beat.notes:
                note = gp.Note(beat=beat)
                note.value = source_note.value
                note.velocity = source_note.velocity
                note.string = source_note.string
                note.effect = copy.deepcopy(source_note.effect)
                note.durationPercent = source_note.durationPercent
                note.swapAccidentals = source_note.swapAccidentals
                note.type = source_note.type

                if note.type in (gp.NoteType.normal, gp.NoteType.tie):
                    note.value += TRANSPOSE_SEMITONES

                if note.value > target_track.fretCount:
                    raise gp.GPException(
                        f"transposed fret {note.value} exceeds fretCount {target_track.fretCount}"
                    )

                beat.notes.append(note)
            voice.beats.append(beat)
        measure.voices.append(voice)

    return measure


def configure_track(source: gp.Track, target: gp.Track) -> None:
    """Copy non-measure track settings from the arrangement track."""
    target.fretCount = source.fretCount
    target.offset = source.offset
    target.isPercussionTrack = source.isPercussionTrack
    target.is12StringedGuitarTrack = source.is12StringedGuitarTrack
    target.isBanjoTrack = source.isBanjoTrack
    target.isVisible = source.isVisible
    target.isSolo = source.isSolo
    target.isMute = source.isMute
    target.indicateTuning = source.indicateTuning
    target.port = source.port
    target.useRSE = source.useRSE
    target.clefTranspose = source.clefTranspose
    target.clefTransposeSecondary = source.clefTransposeSecondary
    target.strings = copy.deepcopy(source.strings)
    target.channel = copy.deepcopy(source.channel)
    target.color = copy.deepcopy(source.color)
    target.settings = copy.deepcopy(source.settings)
    target.rse = copy.deepcopy(source.rse)


def main() -> None:
    """Build the complete v4 score and write it to disk."""
    main_song = gp.parse(VOCAL_PATH)
    arrangement_song = gp.parse(ARRANGEMENT_PATH)

    arrangement_track = arrangement_song.tracks[0]
    arrangement_target = gp.Track(
        song=main_song,
        number=len(main_song.tracks) + 1,
        name=arrangement_track.name,
        measures=[],
    )
    configure_track(arrangement_track, arrangement_target)
    main_song.tracks.append(arrangement_target)

    measure_map = build_measure_map()

    for index, header in enumerate(main_song.measureHeaders, start=1):
        source_index = measure_map.get(index)
        if source_index is None:
            arrangement_target.measures.append(
                gp.Measure(track=arrangement_target, header=header)
            )
            continue

        arrangement_target.measures.append(
            clone_measure(
                arrangement_track.measures[source_index - 1],
                arrangement_target,
                header,
            )
        )

    # NO MANUAL METADATA COPYING NEEDED!
    # The library now automatically regenerates container metadata on write.

    gp.write(main_song, OUTPUT_PATH, version=(6, 0, 0))
    print(f"✓ Wrote {OUTPUT_PATH}")
    
    # Verify the output
    verify = gp.parse(OUTPUT_PATH)
    print(f"✓ Verified: {len(verify.tracks)} tracks")
    
    for name, content in verify.format_extras.container_files:
        if name == 'misc.xml':
            misc_xml = content.decode('utf-8')
            if f'<PreferredTrackCount>{len(verify.tracks)}</PreferredTrackCount>' in misc_xml:
                print(f"✓ Container metadata correctly shows {len(verify.tracks)} tracks")
            else:
                print(f"⚠ WARNING: Container metadata mismatch!")


if __name__ == "__main__":
    main()
