"""
GPIF (Guitar Pro Interchange Format) XML writer.

This writer converts PyGuitarPro ``Song`` objects into score.gpif XML.
Implementation derived from alphaTab's GpifWriter.ts.

SPDX-License-Identifier: MPL-2.0
Based on: https://github.com/CoderLine/alphaTab (GpifWriter.ts)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from ..models import (
    ArtificialHarmonic,
    Beat,
    BeatStrokeDirection,
    BeatStatus,
    BendEffect,
    Chord,
    Duration,
    Fingering,
    GpifAutomation,
    GpifExtras,
    Note,
    NoteType,
    Octave,
    PinchHarmonic,
    SemiHarmonic,
    SlapEffect,
    SlideType,
    Song,
    TappedHarmonic,
    Track,
    TripletFeel,
    Velocities,
)

__all__ = ['GpifWriter']

_BEND_POSITION_TO_GPIF = 100.0 / BendEffect.maxPosition
_BEND_VALUE_TO_GPIF = 25.0


def _duration_to_gpif(value: int) -> str:
    mapping = {
        Duration.whole: 'Whole',
        Duration.half: 'Half',
        Duration.quarter: 'Quarter',
        Duration.eighth: 'Eighth',
        Duration.sixteenth: '16th',
        Duration.thirtySecond: '32nd',
        Duration.sixtyFourth: '64th',
        Duration.hundredTwentyEighth: '128th',
    }
    return mapping.get(value, 'Quarter')


def _fingering_to_gpif(finger: Fingering) -> Optional[str]:
    mapping = {
        Fingering.thumb: 'P',
        Fingering.index: 'I',
        Fingering.middle: 'M',
        Fingering.annular: 'A',
        Fingering.little: 'C',
    }
    return mapping.get(finger)


def _velocity_to_dynamic(velocity: int) -> str:
    if velocity <= Velocities.pianoPianissimo:
        return 'PPP'
    if velocity <= Velocities.pianissimo:
        return 'PP'
    if velocity <= Velocities.piano:
        return 'P'
    if velocity <= Velocities.mezzoPiano:
        return 'MP'
    if velocity <= Velocities.mezzoForte:
        return 'MF'
    if velocity <= Velocities.forte:
        return 'F'
    if velocity <= Velocities.fortissimo:
        return 'FF'
    return 'FFF'


def _add_simple_property(props_el: ET.Element, name: str, child_tag: str, text: Optional[str]) -> None:
    prop = ET.SubElement(props_el, 'Property', {'name': name})
    child = ET.SubElement(prop, child_tag)
    if text is not None:
        child.text = text


def _write_bend_or_whammy_props(
    props_el: ET.Element,
    bend: BendEffect,
    prefix: str,
    flag_prop: str,
) -> None:
    if not bend.points:
        return
    _add_simple_property(props_el, flag_prop, 'Enable', None)
    pts = bend.points
    origin = pts[0]
    dest = pts[-1]
    _add_simple_property(props_el, f'{prefix}OriginValue', 'Float', f'{origin.value * _BEND_VALUE_TO_GPIF:g}')
    _add_simple_property(props_el, f'{prefix}OriginOffset', 'Float', f'{origin.position * _BEND_POSITION_TO_GPIF:g}')
    if len(pts) == 3:
        mid = pts[1]
        _add_simple_property(props_el, f'{prefix}MiddleValue', 'Float', f'{mid.value * _BEND_VALUE_TO_GPIF:g}')
        _add_simple_property(
            props_el, f'{prefix}MiddleOffset1', 'Float', f'{mid.position * _BEND_POSITION_TO_GPIF:g}'
        )
        _add_simple_property(
            props_el, f'{prefix}MiddleOffset2', 'Float', f'{mid.position * _BEND_POSITION_TO_GPIF:g}'
        )
    elif len(pts) >= 4:
        mid1 = pts[1]
        mid2 = pts[2]
        _add_simple_property(props_el, f'{prefix}MiddleValue', 'Float', f'{mid1.value * _BEND_VALUE_TO_GPIF:g}')
        _add_simple_property(
            props_el, f'{prefix}MiddleOffset1', 'Float', f'{mid1.position * _BEND_POSITION_TO_GPIF:g}'
        )
        _add_simple_property(
            props_el, f'{prefix}MiddleOffset2', 'Float', f'{mid2.position * _BEND_POSITION_TO_GPIF:g}'
        )
    _add_simple_property(props_el, f'{prefix}DestinationValue', 'Float', f'{dest.value * _BEND_VALUE_TO_GPIF:g}')
    _add_simple_property(
        props_el, f'{prefix}DestinationOffset', 'Float', f'{dest.position * _BEND_POSITION_TO_GPIF:g}'
    )


class GpifWriter:
    """
    Serializes a PyGuitarPro ``Song`` into a GPIF XML document.

    Derived from alphaTab's ``GpifWriter``.
    """

    def write(self, song: Song, target_major_version: int = 7) -> bytes:
        """
        Serialize a ``Song`` to UTF-8 GPIF XML bytes.

        :param song: Source ``Song`` model
        :param target_major_version: Target Guitar Pro major version (6, 7, or 8)
        :return: UTF-8 encoded XML bytes
        """
        extras = song.format_extras or GpifExtras()
        root = ET.Element('GPIF')

        gp_version = extras.gp_version or str(target_major_version)
        if target_major_version in (6, 7, 8) and not extras.gp_version:
            gp_version = str(target_major_version)
        ET.SubElement(root, 'GPVersion').text = gp_version
        ET.SubElement(root, 'GPRevision').text = extras.gp_revision or ('9063' if target_major_version == 6 else '10000')
        enc = ET.SubElement(root, 'Encoding')
        ET.SubElement(enc, 'EncodingDescription').text = (
            extras.encoding_description or f'GP{target_major_version}'
        )

        self._write_score(root, song)
        self._write_master_track(root, song, extras)

        tracks_el = ET.SubElement(root, 'Tracks')
        master_bars_el = ET.SubElement(root, 'MasterBars')
        bars_el = ET.SubElement(root, 'Bars')
        voices_el = ET.SubElement(root, 'Voices')
        beats_el = ET.SubElement(root, 'Beats')
        notes_el = ET.SubElement(root, 'Notes')
        rhythms_el = ET.SubElement(root, 'Rhythms')

        # Track IDs and chords
        track_chord_maps: List[Dict[Chord, str]] = []
        for t_idx, track in enumerate(song.tracks):
            chord_map = self._write_track(tracks_el, t_idx, track, extras)
            track_chord_maps.append(chord_map)

        rhythm_ids: Dict[Tuple[int, int, int, int], str] = {}
        next_bar_id = 0
        next_voice_id = 0
        next_beat_id = 0
        next_note_id = 0

        for mb_idx, header in enumerate(song.measureHeaders):
            mb_el = ET.SubElement(master_bars_el, 'MasterBar')
            if mb_idx == 0 or (
                header.timeSignature != song.measureHeaders[mb_idx - 1].timeSignature
            ):
                ET.SubElement(mb_el, 'Time').text = (
                    f'{header.timeSignature.numerator}/{header.timeSignature.denominator.value}'
                )
            if header.hasDoubleBar:
                ET.SubElement(mb_el, 'DoubleBar')
            if header.isRepeatOpen or header.repeatClose > 0:
                attrs: Dict[str, str] = {}
                if header.isRepeatOpen:
                    attrs['start'] = 'true'
                if header.repeatClose > 0:
                    attrs['end'] = 'true'
                    attrs['count'] = str(header.repeatClose)
                ET.SubElement(mb_el, 'Repeat', attrs)
            if header.repeatAlternative > 0:
                alts = [str(bit + 1) for bit in range(8) if header.repeatAlternative & (1 << bit)]
                if alts:
                    ET.SubElement(mb_el, 'AlternateEndings').text = ' '.join(alts)
            if header.marker is not None and header.marker.title:
                sec = ET.SubElement(mb_el, 'Section')
                ET.SubElement(sec, 'Text').text = header.marker.title
            if header.tripletFeel != TripletFeel.none:
                feel_str = 'Triplet8th' if header.tripletFeel == TripletFeel.eighth else 'Triplet16th'
                ET.SubElement(mb_el, 'TripletFeel').text = feel_str
            if mb_idx == 0 or header.keySignature != song.measureHeaders[mb_idx - 1].keySignature:
                key_el = ET.SubElement(mb_el, 'Key')
                acc, mode = header.keySignature.value
                ET.SubElement(key_el, 'AccidentalCount').text = str(acc)
                ET.SubElement(key_el, 'Mode').text = 'Minor' if mode == 1 else 'Major'

            bar_ids_for_mb: List[str] = []
            for t_idx, track in enumerate(song.tracks):
                if mb_idx >= len(track.measures):
                    bar_ids_for_mb.append('-1')
                    continue
                measure = track.measures[mb_idx]
                bar_id = str(next_bar_id)
                next_bar_id += 1
                bar_ids_for_mb.append(bar_id)

                bar_el = ET.SubElement(bars_el, 'Bar', {'id': bar_id})
                voice_ids_for_bar: List[str] = []
                for voice in measure.voices:
                    if not voice.beats:
                        voice_ids_for_bar.append('-1')
                        continue
                    voice_id = str(next_voice_id)
                    next_voice_id += 1
                    voice_ids_for_bar.append(voice_id)

                    voice_el = ET.SubElement(voices_el, 'Voice', {'id': voice_id})
                    beat_ids_for_voice: List[str] = []
                    for beat in voice.beats:
                        beat_id = str(next_beat_id)
                        next_beat_id += 1
                        beat_ids_for_voice.append(beat_id)

                        r_key = (
                            beat.duration.value,
                            1 if beat.duration.isDotted else 0,
                            beat.duration.tuplet.enters,
                            beat.duration.tuplet.times,
                        )
                        if r_key not in rhythm_ids:
                            rid = str(len(rhythm_ids))
                            rhythm_ids[r_key] = rid
                            self._write_rhythm(rhythms_el, rid, r_key)
                        rid = rhythm_ids[r_key]

                        note_ids_for_beat: List[str] = []
                        for note in beat.notes:
                            note_id = str(next_note_id)
                            next_note_id += 1
                            note_ids_for_beat.append(note_id)
                            self._write_note(notes_el, note_id, note)

                        self._write_beat(
                            beats_el,
                            beat_id,
                            beat,
                            rid,
                            note_ids_for_beat,
                            track_chord_maps[t_idx],
                        )

                    ET.SubElement(voice_el, 'Beats').text = ' '.join(beat_ids_for_voice)

                ET.SubElement(bar_el, 'Voices').text = ' '.join(voice_ids_for_bar)

            ET.SubElement(mb_el, 'Bars').text = ' '.join(bar_ids_for_mb)

        xml_bytes = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        return xml_bytes

    def _write_score(self, root: ET.Element, song: Song) -> None:
        score_el = ET.SubElement(root, 'Score')
        ET.SubElement(score_el, 'Title').text = song.title
        ET.SubElement(score_el, 'SubTitle').text = song.subtitle
        ET.SubElement(score_el, 'Artist').text = song.artist
        ET.SubElement(score_el, 'Album').text = song.album
        ET.SubElement(score_el, 'Words').text = song.words
        ET.SubElement(score_el, 'Music').text = song.music
        ET.SubElement(score_el, 'Copyright').text = song.copyright
        ET.SubElement(score_el, 'Tabber').text = song.tab
        ET.SubElement(score_el, 'Instructions').text = song.instructions
        ET.SubElement(score_el, 'Notices').text = '\n'.join(song.notice) if song.notice else ''

    def _write_master_track(self, root: ET.Element, song: Song, extras: GpifExtras) -> None:
        mt_el = ET.SubElement(root, 'MasterTrack')
        ET.SubElement(mt_el, 'Tracks').text = ' '.join(str(i) for i in range(len(song.tracks)))
        if extras.master_track_anacrusis:
            ET.SubElement(mt_el, 'Anacrusis')

        autos_el = ET.SubElement(mt_el, 'Automations')
        wrote_tempo = False
        for auto in extras.automations:
            self._write_automation(autos_el, auto, song.tempo if (auto.type == 'Tempo' and auto.bar == 0) else None)
            if auto.type == 'Tempo' and auto.bar == 0:
                wrote_tempo = True
        if not wrote_tempo:
            self._write_automation(
                autos_el,
                GpifAutomation(type='Tempo', bar=0, position=0.0, value=f'{song.tempo} 2', linear=False),
                None,
            )

    def _write_automation(self, parent: ET.Element, auto: GpifAutomation, override_tempo: Optional[int]) -> None:
        el = ET.SubElement(parent, 'Automation')
        ET.SubElement(el, 'Type').text = auto.type
        ET.SubElement(el, 'Linear').text = 'true' if auto.linear else 'false'
        ET.SubElement(el, 'Bar').text = str(auto.bar)
        ET.SubElement(el, 'Position').text = f'{auto.position:g}'
        ET.SubElement(el, 'Visible').text = 'true' if auto.visible else 'false'
        if override_tempo is not None:
            parts = auto.value.split()
            suffix = parts[1] if len(parts) > 1 else '2'
            ET.SubElement(el, 'Value').text = f'{override_tempo} {suffix}'
        else:
            ET.SubElement(el, 'Value').text = auto.value

    def _write_track(
        self,
        parent: ET.Element,
        t_idx: int,
        track: Track,
        extras: GpifExtras,
    ) -> Dict[Chord, str]:
        track_el = ET.SubElement(parent, 'Track', {'id': str(t_idx)})
        ET.SubElement(track_el, 'Name').text = track.name
        ET.SubElement(track_el, 'Color').text = f'{track.color.r} {track.color.g} {track.color.b}'
        if track.isSolo:
            ET.SubElement(track_el, 'PlaybackState').text = 'Solo'
        elif track.isMute:
            ET.SubElement(track_el, 'PlaybackState').text = 'Mute'

        gm_attrs = {'table': 'Percussion'} if track.isPercussionTrack else {}
        gm = ET.SubElement(track_el, 'GeneralMidi', gm_attrs)
        ET.SubElement(gm, 'Program').text = str(track.channel.instrument)
        ET.SubElement(gm, 'Port').text = str(track.port)
        ET.SubElement(gm, 'PrimaryChannel').text = str(track.channel.channel)
        ET.SubElement(gm, 'SecondaryChannel').text = str(track.channel.effectChannel)

        if track.clefTranspose is not None and track.clefTranspose != 0:
            tr_el = ET.SubElement(track_el, 'Transpose')
            ET.SubElement(tr_el, 'Octave').text = str(track.clefTranspose // 12)
            ET.SubElement(tr_el, 'Chromatic').text = str(track.clefTranspose % 12)

        # Collect unique chords on this track
        chord_map: Dict[Chord, str] = {}
        for measure in track.measures:
            for voice in measure.voices:
                for beat in voice.beats:
                    chord = beat.effect.chord
                    if chord is not None and chord not in chord_map:
                        chord_map[chord] = str(len(chord_map))

        staves_el = ET.SubElement(track_el, 'Staves')
        staff_el = ET.SubElement(staves_el, 'Staff')
        props_el = ET.SubElement(staff_el, 'Properties')
        _add_simple_property(props_el, 'CapoFret', 'Fret', str(track.offset))
        if track.strings:
            tuning_prop = ET.SubElement(props_el, 'Property', {'name': 'Tuning'})
            pitches_rev = [str(s.value) for s in reversed(track.strings)]
            ET.SubElement(tuning_prop, 'Pitches').text = ' '.join(pitches_rev)

        if chord_map:
            diag_prop = ET.SubElement(props_el, 'Property', {'name': 'DiagramCollection'})
            items_el = ET.SubElement(diag_prop, 'Items')
            for chord, cid in chord_map.items():
                self._write_chord_item(items_el, cid, chord)

        for idx, raw_xml in extras.track_rse_xml:
            if idx == t_idx:
                track_el.append(ET.fromstring(raw_xml))
        for idx, raw_xml in extras.track_sounds_xml:
            if idx == t_idx:
                track_el.append(ET.fromstring(raw_xml))
        for idx, raw_xml in extras.track_automations_xml:
            if idx == t_idx:
                track_el.append(ET.fromstring(raw_xml))

        return chord_map

    def _write_chord_item(self, items_el: ET.Element, cid: str, chord: Chord) -> None:
        item = ET.SubElement(items_el, 'Item', {'id': cid, 'name': chord.name})
        base_fret = max(0, (chord.firstFret or 1) - 1)
        string_count = max(1, len(chord.strings))
        diag = ET.SubElement(item, 'Diagram', {'stringCount': str(string_count), 'baseFret': str(base_fret)})
        for pos, fret in enumerate(chord.strings):
            if fret >= 0:
                s_idx = string_count - pos - 1
                ET.SubElement(diag, 'Fret', {'string': str(s_idx), 'fret': str(max(0, fret - base_fret))})
        if chord.show is not None:
            ET.SubElement(diag, 'Property', {'name': 'ShowName', 'value': 'true' if chord.show else 'false'})

    def _write_rhythm(
        self,
        rhythms_el: ET.Element,
        rid: str,
        r_key: Tuple[int, int, int, int],
    ) -> None:
        val, dots, enters, times = r_key
        r_el = ET.SubElement(rhythms_el, 'Rhythm', {'id': rid})
        ET.SubElement(r_el, 'NoteValue').text = _duration_to_gpif(val)
        if dots > 0:
            ET.SubElement(r_el, 'AugmentationDot', {'count': str(dots)})
        if enters != 1 or times != 1:
            ET.SubElement(r_el, 'PrimaryTuplet', {'num': str(enters), 'den': str(times)})

    def _write_beat(
        self,
        beats_el: ET.Element,
        beat_id: str,
        beat: Beat,
        rhythm_id: str,
        note_ids: List[str],
        chord_map: Dict[Chord, str],
    ) -> None:
        b_el = ET.SubElement(beats_el, 'Beat', {'id': beat_id})
        if note_ids:
            ET.SubElement(b_el, 'Notes').text = ' '.join(note_ids)
        ET.SubElement(b_el, 'Rhythm', {'ref': rhythm_id})

        if beat.notes:
            ET.SubElement(b_el, 'Dynamic').text = _velocity_to_dynamic(beat.notes[0].velocity)
        if beat.text:
            ET.SubElement(b_el, 'FreeText').text = beat.text

        eff = beat.effect
        if eff.chord is not None and eff.chord in chord_map:
            ET.SubElement(b_el, 'Chord').text = chord_map[eff.chord]
        if eff.fadeIn:
            ET.SubElement(b_el, 'Fadding').text = 'FadeIn'

        if beat.octave != Octave.none:
            oct_map = {
                Octave.ottava: '8va',
                Octave.quindicesima: '15ma',
                Octave.ottavaBassa: '8vb',
                Octave.quindicesimaBassa: '15mb',
            }
            if beat.octave in oct_map:
                ET.SubElement(b_el, 'Ottavia').text = oct_map[beat.octave]

        # Note-level beat-wide effects (tremolo picking, grace)
        if beat.notes:
            n0_eff = beat.notes[0].effect
            if n0_eff.tremoloPicking is not None:
                tp_val = n0_eff.tremoloPicking.duration.value
                tp_map = {
                    Duration.eighth: '1/2',
                    Duration.sixteenth: '1/4',
                    Duration.thirtySecond: '1/8',
                }
                if tp_val in tp_map:
                    ET.SubElement(b_el, 'Tremolo').text = tp_map[tp_val]
            if n0_eff.grace is not None:
                ET.SubElement(b_el, 'GraceNotes').text = 'OnBeat' if n0_eff.grace.isOnBeat else 'BeforeBeat'

        props_el = ET.SubElement(b_el, 'Properties')
        if eff.stroke.direction != BeatStrokeDirection.none:
            _add_simple_property(
                props_el,
                'Brush',
                'Direction',
                'Up' if eff.stroke.direction == BeatStrokeDirection.up else 'Down',
            )
        if eff.pickStroke != BeatStrokeDirection.none:
            _add_simple_property(
                props_el,
                'PickStroke',
                'Direction',
                'Up' if eff.pickStroke == BeatStrokeDirection.up else 'Down',
            )
        if eff.slapEffect == SlapEffect.slapping:
            _add_simple_property(props_el, 'Slapped', 'Enable', None)
        elif eff.slapEffect == SlapEffect.popping:
            _add_simple_property(props_el, 'Popped', 'Enable', None)
        if eff.vibrato:
            _add_simple_property(props_el, 'VibratoWTremBar', 'Strength', 'Slight')
        if eff.hasRasgueado:
            _add_simple_property(props_el, 'Rasgueado', 'Rasgueado', 'ii_1')
        if eff.tremoloBar is not None:
            _write_bend_or_whammy_props(props_el, eff.tremoloBar, 'WhammyBar', 'WhammyBar')

    def _write_note(self, notes_el: ET.Element, note_id: str, note: Note) -> None:
        n_el = ET.SubElement(notes_el, 'Note', {'id': note_id})
        eff = note.effect

        if note.type == NoteType.tie:
            ET.SubElement(n_el, 'Tie', {'destination': 'true'})
        if eff.ghostNote:
            ET.SubElement(n_el, 'AntiAccent').text = 'Normal'
        if eff.letRing:
            ET.SubElement(n_el, 'LetRing')
        if eff.vibrato:
            ET.SubElement(n_el, 'Vibrato').text = 'Slight'
        if eff.trill is not None:
            ET.SubElement(n_el, 'Trill').text = str(eff.trill.fret)

        accent_flags = 0
        if eff.staccato:
            accent_flags |= 0x01
        if eff.heavyAccentuatedNote:
            accent_flags |= 0x04
        if eff.accentuatedNote:
            accent_flags |= 0x08
        if accent_flags:
            ET.SubElement(n_el, 'Accent').text = str(accent_flags)

        lf = _fingering_to_gpif(eff.leftHandFinger)
        if lf is not None:
            ET.SubElement(n_el, 'LeftFingering').text = lf
        rf = _fingering_to_gpif(eff.rightHandFinger)
        if rf is not None:
            ET.SubElement(n_el, 'RightFingering').text = rf

        props_el = ET.SubElement(n_el, 'Properties')
        _add_simple_property(props_el, 'String', 'String', str(max(0, note.string - 1)))
        _add_simple_property(props_el, 'Fret', 'Fret', str(note.value))

        if note.type == NoteType.dead:
            _add_simple_property(props_el, 'Muted', 'Enable', None)
        if eff.palmMute:
            _add_simple_property(props_el, 'PalmMuted', 'Enable', None)
        if eff.hammer:
            _add_simple_property(props_el, 'HopoOrigin', 'Enable', None)

        if eff.harmonic is not None:
            h = eff.harmonic
            if isinstance(h, ArtificialHarmonic):
                _add_simple_property(props_el, 'HarmonicType', 'HType', 'Artificial')
            elif isinstance(h, TappedHarmonic):
                _add_simple_property(props_el, 'HarmonicType', 'HType', 'Tap')
                if h.fret is not None:
                    _add_simple_property(props_el, 'HarmonicFret', 'HFret', str(h.fret))
            elif isinstance(h, PinchHarmonic):
                _add_simple_property(props_el, 'HarmonicType', 'HType', 'Pinch')
            elif isinstance(h, SemiHarmonic):
                _add_simple_property(props_el, 'HarmonicType', 'HType', 'Semi')
            else:
                _add_simple_property(props_el, 'HarmonicType', 'HType', 'Natural')

        if eff.slides:
            slide_flags = 0
            for slide in eff.slides:
                if slide == SlideType.shiftSlideTo:
                    slide_flags |= 1
                elif slide == SlideType.legatoSlideTo:
                    slide_flags |= 2
                elif slide == SlideType.outDownwards:
                    slide_flags |= 4
                elif slide == SlideType.outUpwards:
                    slide_flags |= 8
                elif slide == SlideType.intoFromBelow:
                    slide_flags |= 16
                elif slide == SlideType.intoFromAbove:
                    slide_flags |= 32
            if slide_flags:
                _add_simple_property(props_el, 'Slide', 'Flags', str(slide_flags))

        if eff.bend is not None:
            _write_bend_or_whammy_props(props_el, eff.bend, 'Bend', 'Bended')
