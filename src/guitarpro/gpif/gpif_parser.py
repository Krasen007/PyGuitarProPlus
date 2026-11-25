"""
GPIF (Guitar Pro Interchange Format) XML parser.

This parser reads score.gpif XML and converts it to PyGuitarPro model objects.
Implementation derived from alphaTab's GpifParser.ts.

SPDX-License-Identifier: MPL-2.0
Based on: https://github.com/CoderLine/alphaTab (GpifParser.ts)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..models import (
    ArtificialHarmonic,
    Beat,
    BeatEffect,
    BeatStroke,
    BeatStrokeDirection,
    BeatStatus,
    BendEffect,
    BendPoint,
    BendType,
    Chord,
    Color,
    Duration,
    Fingering,
    GpifAutomation,
    GpifExtras,
    GraceEffect,
    GuitarString,
    HarmonicEffect,
    KeySignature,
    Marker,
    Measure,
    MeasureHeader,
    NaturalHarmonic,
    Note,
    NoteEffect,
    NoteType,
    Octave,
    PinchHarmonic,
    PitchClass,
    RepeatGroup,
    SemiHarmonic,
    SlapEffect,
    SlideType,
    Song,
    TappedHarmonic,
    TimeSignature,
    Track,
    TremoloPickingEffect,
    TrillEffect,
    TripletFeel,
    Tuplet,
    Velocities,
    Voice,
)

__all__ = ['GpifParser', 'GpifParseError']

_INVALID_ID = '-1'
_BEND_POSITION_FACTOR = BendEffect.maxPosition / 100.0
_BEND_VALUE_FACTOR = 1.0 / 25.0


class GpifParseError(Exception):
    """Raised when GPIF parsing fails."""


@dataclass
class _GpifRhythm:
    id: str = ''
    dots: int = 0
    tuplet_numerator: int = 1
    tuplet_denominator: int = 1
    value: int = Duration.quarter


@dataclass
class _GpifNoteData:
    id: str = ''
    string: int = 1
    fret: int = 0
    is_tie_destination: bool = False
    is_dead: bool = False
    is_ghost: bool = False
    is_let_ring: bool = False
    is_palm_mute: bool = False
    is_vibrato: bool = False
    is_hammer_origin: bool = False
    is_staccato: bool = False
    accent_normal: bool = False
    accent_heavy: bool = False
    left_finger: Fingering = Fingering.open
    right_finger: Fingering = Fingering.open
    slides: List[SlideType] = field(default_factory=list)
    harmonic: Optional[HarmonicEffect] = None
    trill_fret: int = -1
    bend: Optional[BendEffect] = None


@dataclass
class _GpifBeatData:
    id: str = ''
    note_ids: List[str] = field(default_factory=list)
    rhythm_id: str = ''
    text: Optional[str] = None
    chord_id: Optional[str] = None
    velocity: int = Velocities.default
    fade_in: bool = False
    tremolo_picking: Optional[TremoloPickingEffect] = None
    grace_on_beat: Optional[bool] = None
    brush_direction: BeatStrokeDirection = BeatStrokeDirection.none
    pick_stroke: BeatStrokeDirection = BeatStrokeDirection.none
    slap_effect: SlapEffect = SlapEffect.none
    has_rasgueado: bool = False
    vibrato: bool = False
    whammy: Optional[BendEffect] = None
    octave: Octave = Octave.none


@dataclass
class _GpifVoiceData:
    id: str = ''
    beat_ids: List[str] = field(default_factory=list)


@dataclass
class _GpifBarData:
    id: str = ''
    voice_ids: List[str] = field(default_factory=list)


@dataclass
class _GpifMasterBarData:
    numerator: int = 4
    denominator: int = 4
    has_double_bar: bool = False
    is_repeat_open: bool = False
    repeat_close: int = -1
    repeat_alternative: int = 0
    triplet_feel: TripletFeel = TripletFeel.none
    key_accidental: int = 0
    key_mode: int = 0
    has_key: bool = False
    marker_text: str = ''
    bar_ids: List[str] = field(default_factory=list)


@dataclass
class _GpifTrackData:
    id: str = ''
    name: str = 'Track 1'
    color: Color = field(default_factory=lambda: Color(255, 0, 0))
    program: int = 25
    port: int = 1
    primary_channel: int = 0
    secondary_channel: int = 1
    is_percussion: bool = False
    is_solo: bool = False
    is_mute: bool = False
    pitches: List[int] = field(default_factory=list)
    capo: int = 0
    transpose_semitones: int = 0
    chords_by_id: Dict[str, Chord] = field(default_factory=dict)
    rse_xml: str = ''
    sounds_xml: str = ''
    automations_xml: str = ''


def _split_safe(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return [part for part in text.strip().split() if part]


def _int_safe(text: Optional[str], default: int = 0) -> int:
    if not text:
        return default
    try:
        return int(text.strip())
    except ValueError:
        return default


def _float_safe(text: Optional[str], default: float = 0.0) -> float:
    if not text:
        return default
    try:
        return float(text.strip())
    except ValueError:
        return default


def _to_bend_offset(gpif_offset: float) -> int:
    return max(0, min(BendEffect.maxPosition, round(gpif_offset * _BEND_POSITION_FACTOR)))


def _to_bend_value(gpif_value: float) -> int:
    return round(gpif_value * _BEND_VALUE_FACTOR)


def _parse_fingering(text: Optional[str]) -> Fingering:
    mapping = {
        'P': Fingering.thumb,
        'I': Fingering.index,
        'M': Fingering.middle,
        'A': Fingering.annular,
        'C': Fingering.little,
        'Thumb': Fingering.thumb,
        'Index': Fingering.index,
        'Middle': Fingering.middle,
        'Rank': Fingering.annular,
        'Pinky': Fingering.little,
    }
    if not text:
        return Fingering.open
    return mapping.get(text.strip(), Fingering.open)


def _parse_duration_value(value_text: Optional[str]) -> int:
    value_map = {
        'Long': Duration.whole,
        'DoubleWhole': Duration.whole,
        'Whole': Duration.whole,
        'Half': Duration.half,
        'Quarter': Duration.quarter,
        'Eighth': Duration.eighth,
        '16th': Duration.sixteenth,
        'Sixteenth': Duration.sixteenth,
        '32nd': Duration.thirtySecond,
        'ThirtySecond': Duration.thirtySecond,
        '64th': Duration.sixtyFourth,
        'SixtyFourth': Duration.sixtyFourth,
        '128th': Duration.hundredTwentyEighth,
        '256th': Duration.hundredTwentyEighth,
    }
    if not value_text:
        return Duration.quarter
    return value_map.get(value_text.strip(), Duration.quarter)


def _safe_key_signature(accidental: int, mode: int) -> KeySignature:
    try:
        return KeySignature((accidental, mode))
    except ValueError:
        return KeySignature.CMajor


def _build_bend_effect(
    origin_val: Optional[float],
    origin_off: Optional[float],
    mid_val: Optional[float],
    mid_off1: Optional[float],
    mid_off2: Optional[float],
    dest_val: Optional[float],
    dest_off: Optional[float],
) -> BendEffect:
    points: List[BendPoint] = []
    p0 = BendPoint(
        position=_to_bend_offset(origin_off or 0.0),
        value=_to_bend_value(origin_val or 0.0),
    )
    points.append(p0)

    if mid_val is not None:
        if mid_off1 is not None:
            points.append(BendPoint(position=_to_bend_offset(mid_off1), value=_to_bend_value(mid_val)))
        if mid_off2 is not None:
            points.append(BendPoint(position=_to_bend_offset(mid_off2), value=_to_bend_value(mid_val)))
        if mid_off1 is None and mid_off2 is None:
            points.append(BendPoint(position=BendEffect.maxPosition // 2, value=_to_bend_value(mid_val)))

    p_end = BendPoint(
        position=_to_bend_offset(dest_off if dest_off is not None else 100.0),
        value=_to_bend_value(dest_val or 0.0),
    )
    points.append(p_end)

    max_val = max((p.value for p in points), default=0)
    bend = BendEffect(type=BendType.bend, value=max_val, points=points)
    return bend


class GpifParser:
    """
    Parses a GPIF XML document into a PyGuitarPro ``Song`` object.

    Derived from alphaTab's ``GpifParser``.
    """

    def __init__(self) -> None:
        self._gp_version: str = ''
        self._gp_revision: str = ''
        self._encoding_description: str = ''
        self._has_anacrusis: bool = False
        self._automations: List[GpifAutomation] = []
        self._tracks_mapping: List[str] = []
        self._tracks_by_id: Dict[str, _GpifTrackData] = {}
        self._master_bars: List[_GpifMasterBarData] = []
        self._bars_by_id: Dict[str, _GpifBarData] = {}
        self._voices_by_id: Dict[str, _GpifVoiceData] = {}
        self._beats_by_id: Dict[str, _GpifBeatData] = {}
        self._notes_by_id: Dict[str, _GpifNoteData] = {}
        self._rhythms_by_id: Dict[str, _GpifRhythm] = {}
        self._tapped_notes: Set[str] = set()

    def parse(self, gpif_xml: bytes | str) -> Song:
        """
        Parse GPIF XML data into a ``Song`` object.

        :param gpif_xml: Raw GPIF XML bytes or string
        :return: Parsed ``Song`` object
        :raises GpifParseError: If parsing fails
        """
        try:
            root = ET.fromstring(gpif_xml)
        except ET.ParseError as exc:
            raise GpifParseError(f"Invalid XML: {exc}") from exc

        if root.tag != 'GPIF':
            raise GpifParseError(f"Root node of XML was '{root.tag}', expected 'GPIF'")

        self._reset()
        song = Song()
        song.measureHeaders = []
        song.tracks = []

        self._parse_dom(root, song)
        self._build_song(song)
        return song

    def _reset(self) -> None:
        self._gp_version = ''
        self._gp_revision = ''
        self._encoding_description = ''
        self._has_anacrusis = False
        self._automations = []
        self._tracks_mapping = []
        self._tracks_by_id = {}
        self._master_bars = []
        self._bars_by_id = {}
        self._voices_by_id = {}
        self._beats_by_id = {}
        self._notes_by_id = {}
        self._rhythms_by_id = {}
        self._tapped_notes = set()

    def _parse_dom(self, root: ET.Element, song: Song) -> None:
        for child in root:
            tag = child.tag
            if tag == 'GPVersion':
                self._gp_version = (child.text or '').strip()
            elif tag == 'GPRevision':
                self._gp_revision = (child.text or '').strip()
            elif tag == 'Encoding':
                desc = child.find('EncodingDescription')
                if desc is not None and desc.text:
                    self._encoding_description = desc.text.strip()
            elif tag == 'Score':
                self._parse_score_node(child, song)
            elif tag == 'MasterTrack':
                self._parse_master_track_node(child)
            elif tag == 'Tracks':
                self._parse_tracks_node(child)
            elif tag == 'MasterBars':
                self._parse_master_bars_node(child)
            elif tag == 'Bars':
                self._parse_bars_node(child)
            elif tag == 'Voices':
                self._parse_voices_node(child)
            elif tag == 'Beats':
                self._parse_beats_node(child)
            elif tag == 'Notes':
                self._parse_notes_node(child)
            elif tag == 'Rhythms':
                self._parse_rhythms_node(child)

    def _parse_score_node(self, node: ET.Element, song: Song) -> None:
        for child in node:
            text = child.text or ''
            tag = child.tag
            if tag == 'Title':
                song.title = text
            elif tag == 'SubTitle':
                song.subtitle = text
            elif tag == 'Artist':
                song.artist = text
            elif tag == 'Album':
                song.album = text
            elif tag == 'Words':
                song.words = text
            elif tag == 'Music':
                song.music = text
            elif tag == 'WordsAndMusic':
                if text and not song.words:
                    song.words = text
                if text and not song.music:
                    song.music = text
            elif tag == 'Copyright':
                song.copyright = text
            elif tag == 'Tabber':
                song.tab = text
            elif tag == 'Instructions':
                song.instructions = text
            elif tag in ('Notices', 'Notice'):
                if text:
                    song.notice = text.splitlines()

    def _parse_master_track_node(self, node: ET.Element) -> None:
        for child in node:
            if child.tag == 'Tracks':
                self._tracks_mapping = _split_safe(child.text)
            elif child.tag == 'Anacrusis':
                self._has_anacrusis = True
            elif child.tag == 'Automations':
                for auto_node in child.findall('Automation'):
                    auto = self._parse_automation(auto_node)
                    if auto is not None:
                        self._automations.append(auto)

    def _parse_automation(self, node: ET.Element) -> Optional[GpifAutomation]:
        auto_type = (node.findtext('Type') or '').strip()
        if not auto_type:
            return None
        bar = _int_safe(node.findtext('Bar'), 0)
        position = _float_safe(node.findtext('Position'), 0.0)
        value = (node.findtext('Value') or '').strip()
        linear = (node.findtext('Linear') or '').strip().lower() == 'true'
        visible = (node.findtext('Visible') or 'true').strip().lower() != 'false'
        return GpifAutomation(
            type=auto_type,
            bar=bar,
            position=position,
            value=value,
            linear=linear,
            visible=visible,
        )

    def _parse_tracks_node(self, node: ET.Element) -> None:
        for track_node in node.findall('Track'):
            self._parse_track(track_node)

    def _parse_track(self, node: ET.Element) -> None:
        td = _GpifTrackData(id=node.get('id', ''))
        for child in node:
            tag = child.tag
            if tag == 'Name':
                td.name = child.text or ''
            elif tag == 'Color':
                parts = _split_safe(child.text)
                if len(parts) >= 3:
                    td.color = Color(
                        _int_safe(parts[0], 255),
                        _int_safe(parts[1], 0),
                        _int_safe(parts[2], 0),
                    )
            elif tag == 'PlaybackState':
                state = (child.text or '').strip()
                td.is_solo = state == 'Solo'
                td.is_mute = state == 'Mute'
            elif tag in ('GeneralMidi', 'MidiConnection', 'MIDISettings'):
                if child.get('table') == 'Percussion':
                    td.is_percussion = True
                prog = child.findtext('Program')
                if prog is not None:
                    td.program = _int_safe(prog, td.program)
                port = child.findtext('Port')
                if port is not None:
                    td.port = _int_safe(port, td.port)
                pc = child.findtext('PrimaryChannel')
                if pc is not None:
                    td.primary_channel = _int_safe(pc, td.primary_channel)
                sc = child.findtext('SecondaryChannel')
                if sc is not None:
                    td.secondary_channel = _int_safe(sc, td.secondary_channel)
            elif tag == 'Properties':
                self._parse_track_or_staff_properties(child, td)
            elif tag == 'Staves':
                first_staff = child.find('Staff')
                if first_staff is not None:
                    props = first_staff.find('Properties')
                    if props is not None:
                        self._parse_track_or_staff_properties(props, td)
            elif tag == 'Transpose':
                octave = _int_safe(child.findtext('Octave'), 0)
                chromatic = _int_safe(child.findtext('Chromatic'), 0)
                td.transpose_semitones = octave * 12 + chromatic
            elif tag == 'PartSounding':
                pitch = child.findtext('TranspositionPitch')
                if pitch is not None:
                    td.transpose_semitones = _int_safe(pitch, 0)
            elif tag == 'RSE':
                td.rse_xml = ET.tostring(child, encoding='unicode').strip()
            elif tag == 'Sounds':
                td.sounds_xml = ET.tostring(child, encoding='unicode').strip()
                first_midi = child.find('Sound/MIDI/Program')
                if first_midi is not None and first_midi.text:
                    td.program = _int_safe(first_midi.text, td.program)
            elif tag == 'Automations':
                td.automations_xml = ET.tostring(child, encoding='unicode').strip()

        self._tracks_by_id[td.id] = td

    def _parse_track_or_staff_properties(self, props_node: ET.Element, td: _GpifTrackData) -> None:
        for prop in props_node.findall('Property'):
            name = prop.get('name', '')
            if name == 'Tuning':
                pitches_text = prop.findtext('Pitches')
                parts = _split_safe(pitches_text)
                if parts:
                    # GPIF stores lowest-to-highest; PyGuitarPro stores highest-to-lowest (string 1..N)
                    td.pitches = [_int_safe(p, 0) for p in reversed(parts)]
            elif name == 'CapoFret':
                td.capo = _int_safe(prop.findtext('Fret'), 0)
            elif name in ('DiagramCollection', 'ChordCollection'):
                items = prop.find('Items')
                if items is not None:
                    for item in items.findall('Item'):
                        chord_id = item.get('id', '')
                        chord = self._parse_chord_item(item)
                        if chord_id and chord is not None:
                            td.chords_by_id[chord_id] = chord

    def _parse_chord_item(self, item: ET.Element) -> Optional[Chord]:
        diagram = item.find('Diagram')
        name = item.get('name', '')
        if diagram is None:
            return Chord(length=6, name=name, show=False)

        string_count = max(1, _int_safe(diagram.get('stringCount'), 6))
        base_fret = _int_safe(diagram.get('baseFret'), 0)
        chord = Chord(length=string_count, name=name, firstFret=base_fret + 1)
        chord.strings = [-1] * string_count

        for child in diagram:
            if child.tag == 'Fret':
                s_idx = _int_safe(child.get('string'), 0)
                fret_val = _int_safe(child.get('fret'), 0)
                pos = string_count - s_idx - 1
                if 0 <= pos < string_count:
                    chord.strings[pos] = base_fret + fret_val
            elif child.tag == 'Property':
                pname = child.get('name', '')
                if pname == 'ShowName':
                    chord.show = child.get('value', '').lower() == 'true'
        return chord

    def _parse_master_bars_node(self, node: ET.Element) -> None:
        for mb_node in node.findall('MasterBar'):
            mb = _GpifMasterBarData()
            for child in mb_node:
                tag = child.tag
                if tag == 'Time':
                    parts = (child.text or '').split('/')
                    if len(parts) == 2:
                        mb.numerator = _int_safe(parts[0], 4)
                        mb.denominator = _int_safe(parts[1], 4)
                elif tag == 'DoubleBar':
                    mb.has_double_bar = True
                elif tag == 'Repeat':
                    if (child.get('start') or '').lower() == 'true':
                        mb.is_repeat_open = True
                    if (child.get('end') or '').lower() == 'true':
                        mb.repeat_close = _int_safe(child.get('count'), 1)
                elif tag == 'AlternateEndings':
                    mask = 0
                    for alt in _split_safe(child.text):
                        val = _int_safe(alt, 0)
                        if val > 0:
                            mask |= 1 << (val - 1)
                    mb.repeat_alternative = mask
                elif tag == 'Bars':
                    mb.bar_ids = _split_safe(child.text)
                elif tag == 'Section':
                    text_el = child.find('Text')
                    letter_el = child.find('Letter')
                    text_val = (text_el.text if text_el is not None else '') or ''
                    letter_val = (letter_el.text if letter_el is not None else '') or ''
                    if text_val or letter_val:
                        mb.marker_text = text_val or letter_val
                    elif child.text and child.text.strip():
                        mb.marker_text = child.text.strip()
                elif tag == 'TripletFeel':
                    feel = (child.text or '').strip()
                    if feel == 'Triplet8th':
                        mb.triplet_feel = TripletFeel.eighth
                    elif feel == 'Triplet16th':
                        mb.triplet_feel = TripletFeel.sixteenth
                    else:
                        mb.triplet_feel = TripletFeel.none
                elif tag == 'Key':
                    mb.has_key = True
                    mb.key_accidental = _int_safe(child.findtext('AccidentalCount'), 0)
                    mode_text = (child.findtext('Mode') or 'Major').strip().lower()
                    mb.key_mode = 1 if mode_text == 'minor' else 0
            self._master_bars.append(mb)

    def _parse_bars_node(self, node: ET.Element) -> None:
        for bar_node in node.findall('Bar'):
            bar_id = bar_node.get('id', '')
            voice_ids = _split_safe(bar_node.findtext('Voices'))
            self._bars_by_id[bar_id] = _GpifBarData(id=bar_id, voice_ids=voice_ids)

    def _parse_voices_node(self, node: ET.Element) -> None:
        for voice_node in node.findall('Voice'):
            voice_id = voice_node.get('id', '')
            beat_ids = _split_safe(voice_node.findtext('Beats'))
            self._voices_by_id[voice_id] = _GpifVoiceData(id=voice_id, beat_ids=beat_ids)

    def _parse_beats_node(self, node: ET.Element) -> None:
        dyn_map = {
            'PPP': Velocities.pianoPianissimo,
            'PP': Velocities.pianissimo,
            'P': Velocities.piano,
            'MP': Velocities.mezzoPiano,
            'MF': Velocities.mezzoForte,
            'F': Velocities.forte,
            'FF': Velocities.fortissimo,
            'FFF': Velocities.forteFortissimo,
        }
        ottava_map = {
            '8va': Octave.ottava,
            '15ma': Octave.quindicesima,
            '8vb': Octave.ottavaBassa,
            '15mb': Octave.quindicesimaBassa,
        }
        for beat_node in node.findall('Beat'):
            bd = _GpifBeatData(id=beat_node.get('id', ''))
            for child in beat_node:
                tag = child.tag
                if tag == 'Notes':
                    bd.note_ids = _split_safe(child.text)
                elif tag == 'Rhythm':
                    bd.rhythm_id = child.get('ref', '')
                elif tag == 'FreeText':
                    bd.text = child.text or ''
                elif tag == 'Chord':
                    bd.chord_id = (child.text or '').strip()
                elif tag == 'Dynamic':
                    bd.velocity = dyn_map.get((child.text or '').strip(), Velocities.default)
                elif tag == 'Fadding':
                    if (child.text or '').strip() == 'FadeIn':
                        bd.fade_in = True
                elif tag == 'Tremolo':
                    t_map = {
                        '1/2': Duration.eighth,
                        '1/4': Duration.sixteenth,
                        '1/8': Duration.thirtySecond,
                    }
                    dur_val = t_map.get((child.text or '').strip())
                    if dur_val is not None:
                        bd.tremolo_picking = TremoloPickingEffect(duration=Duration(value=dur_val))
                elif tag == 'GraceNotes':
                    val = (child.text or '').strip()
                    if val == 'OnBeat':
                        bd.grace_on_beat = True
                    elif val == 'BeforeBeat':
                        bd.grace_on_beat = False
                elif tag == 'Ottavia':
                    bd.octave = ottava_map.get((child.text or '').strip(), Octave.none)
                elif tag == 'Whammy':
                    bd.whammy = _build_bend_effect(
                        _float_safe(child.get('originValue'), 0.0),
                        _float_safe(child.get('originOffset'), 0.0),
                        _float_safe(child.get('middleValue')) if child.get('middleValue') is not None else None,
                        _float_safe(child.get('middleOffset1')) if child.get('middleOffset1') is not None else None,
                        _float_safe(child.get('middleOffset2')) if child.get('middleOffset2') is not None else None,
                        _float_safe(child.get('destinationValue'), 0.0),
                        _float_safe(child.get('destinationOffset'), 100.0),
                    )
                elif tag == 'Properties':
                    self._parse_beat_properties(child, bd)

            self._beats_by_id[bd.id] = bd

    def _parse_beat_properties(self, props_node: ET.Element, bd: _GpifBeatData) -> None:
        is_whammy = False
        w_origin_val: Optional[float] = None
        w_origin_off: Optional[float] = None
        w_mid_val: Optional[float] = None
        w_mid_off1: Optional[float] = None
        w_mid_off2: Optional[float] = None
        w_dest_val: Optional[float] = None
        w_dest_off: Optional[float] = None

        for prop in props_node.findall('Property'):
            name = prop.get('name', '')
            if name == 'Brush':
                direction = (prop.findtext('Direction') or '').strip()
                bd.brush_direction = BeatStrokeDirection.up if direction == 'Up' else BeatStrokeDirection.down
            elif name == 'PickStroke':
                direction = (prop.findtext('Direction') or '').strip()
                bd.pick_stroke = BeatStrokeDirection.up if direction == 'Up' else BeatStrokeDirection.down
            elif name == 'Slapped' and prop.find('Enable') is not None:
                bd.slap_effect = SlapEffect.slapping
            elif name == 'Popped' and prop.find('Enable') is not None:
                bd.slap_effect = SlapEffect.popping
            elif name == 'VibratoWTremBar':
                if (prop.findtext('Strength') or '').strip() in ('Wide', 'Slight'):
                    bd.vibrato = True
            elif name == 'Rasgueado':
                bd.has_rasgueado = True
            elif name == 'WhammyBar':
                is_whammy = True
            elif name == 'WhammyBarOriginValue':
                w_origin_val = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'WhammyBarOriginOffset':
                w_origin_off = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'WhammyBarMiddleValue':
                w_mid_val = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'WhammyBarMiddleOffset1':
                w_mid_off1 = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'WhammyBarMiddleOffset2':
                w_mid_off2 = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'WhammyBarDestinationValue':
                w_dest_val = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'WhammyBarDestinationOffset':
                w_dest_off = _float_safe(prop.findtext('Float'), 100.0)

        if is_whammy:
            bd.whammy = _build_bend_effect(
                w_origin_val, w_origin_off, w_mid_val, w_mid_off1, w_mid_off2, w_dest_val, w_dest_off
            )

    def _parse_notes_node(self, node: ET.Element) -> None:
        for note_node in node.findall('Note'):
            nd = _GpifNoteData(id=note_node.get('id', ''))
            for child in note_node:
                tag = child.tag
                if tag == 'Properties':
                    self._parse_note_properties(child, nd)
                elif tag == 'AntiAccent':
                    if (child.text or '').strip().lower() == 'normal':
                        nd.is_ghost = True
                elif tag == 'LetRing':
                    nd.is_let_ring = True
                elif tag == 'Trill':
                    nd.trill_fret = _int_safe(child.text, -1)
                elif tag == 'Accent':
                    flags = _int_safe(child.text, 0)
                    if flags & 0x01:
                        nd.is_staccato = True
                    if flags & 0x04:
                        nd.accent_heavy = True
                    if flags & 0x08:
                        nd.accent_normal = True
                elif tag == 'Tie':
                    if (child.get('destination') or '').lower() == 'true':
                        nd.is_tie_destination = True
                elif tag == 'Vibrato':
                    if (child.text or '').strip() in ('Slight', 'Wide'):
                        nd.is_vibrato = True
                elif tag == 'LeftFingering':
                    nd.left_finger = _parse_fingering(child.text)
                elif tag == 'RightFingering':
                    nd.right_finger = _parse_fingering(child.text)

            self._notes_by_id[nd.id] = nd

    def _parse_note_properties(self, props_node: ET.Element, nd: _GpifNoteData) -> None:
        harmonic_type = ''
        harmonic_fret: Optional[int] = None
        is_bended = False
        b_origin_val: Optional[float] = None
        b_origin_off: Optional[float] = None
        b_mid_val: Optional[float] = None
        b_mid_off1: Optional[float] = None
        b_mid_off2: Optional[float] = None
        b_dest_val: Optional[float] = None
        b_dest_off: Optional[float] = None

        for prop in props_node.findall('Property'):
            name = prop.get('name', '')
            if name == 'String':
                nd.string = _int_safe(prop.findtext('String'), 0) + 1
            elif name == 'Fret':
                nd.fret = _int_safe(prop.findtext('Fret'), 0)
            elif name == 'Tapped':
                self._tapped_notes.add(nd.id)
            elif name == 'Muted' and prop.find('Enable') is not None:
                nd.is_dead = True
            elif name == 'PalmMuted' and prop.find('Enable') is not None:
                nd.is_palm_mute = True
            elif name == 'HopoOrigin' and prop.find('Enable') is not None:
                nd.is_hammer_origin = True
            elif name == 'HarmonicType':
                harmonic_type = (prop.findtext('HType') or '').strip().lower()
            elif name == 'HarmonicFret':
                hf_text = prop.findtext('HFret')
                if hf_text is not None:
                    harmonic_fret = int(round(_float_safe(hf_text, 0.0)))
            elif name == 'Slide':
                flags = _int_safe(prop.findtext('Flags'), 0)
                if flags & 1:
                    nd.slides.append(SlideType.shiftSlideTo)
                elif flags & 2:
                    nd.slides.append(SlideType.legatoSlideTo)
                elif flags & 4:
                    nd.slides.append(SlideType.outDownwards)
                elif flags & 8:
                    nd.slides.append(SlideType.outUpwards)
                if flags & 16:
                    nd.slides.append(SlideType.intoFromBelow)
                elif flags & 32:
                    nd.slides.append(SlideType.intoFromAbove)
            elif name == 'Bended':
                is_bended = True
            elif name == 'BendOriginValue':
                b_origin_val = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'BendOriginOffset':
                b_origin_off = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'BendMiddleValue':
                b_mid_val = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'BendMiddleOffset1':
                b_mid_off1 = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'BendMiddleOffset2':
                b_mid_off2 = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'BendDestinationValue':
                b_dest_val = _float_safe(prop.findtext('Float'), 0.0)
            elif name == 'BendDestinationOffset':
                b_dest_off = _float_safe(prop.findtext('Float'), 100.0)

        if harmonic_type and harmonic_type != 'noharmonic':
            if harmonic_type == 'natural':
                nd.harmonic = NaturalHarmonic()
            elif harmonic_type == 'artificial':
                nd.harmonic = ArtificialHarmonic(pitch=PitchClass(0, 0), octave=0)
            elif harmonic_type == 'tap':
                nd.harmonic = TappedHarmonic(fret=harmonic_fret)
            elif harmonic_type == 'pinch':
                nd.harmonic = PinchHarmonic()
            elif harmonic_type == 'semi':
                nd.harmonic = SemiHarmonic()

        if is_bended:
            nd.bend = _build_bend_effect(
                b_origin_val, b_origin_off, b_mid_val, b_mid_off1, b_mid_off2, b_dest_val, b_dest_off
            )

    def _parse_rhythms_node(self, node: ET.Element) -> None:
        for r_node in node.findall('Rhythm'):
            rid = r_node.get('id', '')
            rhythm = _GpifRhythm(id=rid)
            rhythm.value = _parse_duration_value(r_node.findtext('NoteValue'))
            dot_node = r_node.find('AugmentationDot')
            if dot_node is not None:
                rhythm.dots = _int_safe(dot_node.get('count'), 0)
            tuplet_node = r_node.find('PrimaryTuplet')
            if tuplet_node is not None:
                rhythm.tuplet_numerator = _int_safe(tuplet_node.get('num'), 1)
                rhythm.tuplet_denominator = _int_safe(tuplet_node.get('den'), 1)
            self._rhythms_by_id[rid] = rhythm

    def _build_song(self, song: Song) -> None:
        # Apply global initial tempo from MasterTrack automations if present
        for auto in self._automations:
            if auto.type == 'Tempo' and auto.bar == 0:
                parts = _split_safe(auto.value)
                if parts:
                    song.tempo = max(1, int(round(_float_safe(parts[0], float(song.tempo)))))
                    break

        # Build measure headers
        current_start = Duration.quarterTime
        current_key = KeySignature.CMajor
        repeat_group = RepeatGroup()

        for idx, mb in enumerate(self._master_bars):
            header = MeasureHeader()
            header.number = idx + 1
            header.start = current_start
            header.timeSignature = TimeSignature(
                numerator=mb.numerator,
                denominator=Duration(value=mb.denominator),
            )
            if mb.has_key:
                current_key = _safe_key_signature(mb.key_accidental, mb.key_mode)
            header.keySignature = current_key
            header.hasDoubleBar = mb.has_double_bar
            header.isRepeatOpen = mb.is_repeat_open
            header.repeatClose = mb.repeat_close
            header.repeatAlternative = mb.repeat_alternative
            header.tripletFeel = mb.triplet_feel
            if mb.marker_text:
                header.marker = Marker(title=mb.marker_text, color=Color(255, 0, 0))

            if header.isRepeatOpen or (repeat_group.isClosed and header.repeatAlternative <= 0):
                repeat_group = RepeatGroup()
            repeat_group.addMeasureHeader(header)

            song.measureHeaders.append(header)
            current_start += header.length

        # Build tracks in MasterTrack order (or Track order if MasterTrack.Tracks missing)
        ordered_track_ids = [tid for tid in self._tracks_mapping if tid in self._tracks_by_id]
        if not ordered_track_ids:
            ordered_track_ids = list(self._tracks_by_id.keys())

        track_extras_rse: List[Tuple[int, str]] = []
        track_extras_sounds: List[Tuple[int, str]] = []
        track_extras_autos: List[Tuple[int, str]] = []

        for t_idx, tid in enumerate(ordered_track_ids):
            td = self._tracks_by_id[tid]
            track = Track(song)
            track.number = t_idx + 1
            track.name = td.name or f'Track {t_idx + 1}'
            track.color = td.color
            track.isSolo = td.is_solo
            track.isMute = td.is_mute
            track.isPercussionTrack = td.is_percussion
            track.offset = td.capo
            track.clefTranspose = td.transpose_semitones if td.transpose_semitones != 0 else None
            track.port = td.port
            track.channel.channel = td.primary_channel
            track.channel.effectChannel = td.secondary_channel
            track.channel.instrument = td.program
            if td.pitches:
                track.strings = [GuitarString(n, p) for n, p in enumerate(td.pitches, start=1)]
            # Clear auto-created measures and populate per MasterBar
            track.measures = []
            for header in song.measureHeaders:
                measure = Measure(track, header)
                track.measures.append(measure)
            song.tracks.append(track)

            if td.rse_xml:
                track_extras_rse.append((t_idx, td.rse_xml))
            if td.sounds_xml:
                track_extras_sounds.append((t_idx, td.sounds_xml))
            if td.automations_xml:
                track_extras_autos.append((t_idx, td.automations_xml))

        # Populate measures with voices, beats, and notes
        for mb_idx, mb in enumerate(self._master_bars):
            for t_idx, tid in enumerate(ordered_track_ids):
                if t_idx >= len(mb.bar_ids):
                    continue
                bar_id = mb.bar_ids[t_idx]
                if bar_id == _INVALID_ID or bar_id not in self._bars_by_id:
                    continue

                bar_data = self._bars_by_id[bar_id]
                td = self._tracks_by_id[tid]
                measure = song.tracks[t_idx].measures[mb_idx]
                measure.voices = []

                for v_idx, voice_id in enumerate(bar_data.voice_ids):
                    voice = Voice(measure)
                    if voice_id != _INVALID_ID and voice_id in self._voices_by_id:
                        voice_data = self._voices_by_id[voice_id]
                        for beat_id in voice_data.beat_ids:
                            if beat_id != _INVALID_ID and beat_id in self._beats_by_id:
                                beat = self._instantiate_beat(voice, self._beats_by_id[beat_id], td)
                                voice.beats.append(beat)
                    measure.voices.append(voice)

                while len(measure.voices) < Measure.maxVoices:
                    measure.voices.append(Voice(measure))

        song.format_extras = GpifExtras(
            gp_version=self._gp_version,
            gp_revision=self._gp_revision,
            encoding_description=self._encoding_description,
            automations=tuple(self._automations),
            master_track_anacrusis=self._has_anacrusis,
            track_rse_xml=tuple(track_extras_rse),
            track_sounds_xml=tuple(track_extras_sounds),
            track_automations_xml=tuple(track_extras_autos),
        )

    def _instantiate_beat(self, voice: Voice, bd: _GpifBeatData, td: _GpifTrackData) -> Beat:
        beat = Beat(voice)
        rhythm = self._rhythms_by_id.get(bd.rhythm_id)
        if rhythm is not None:
            beat.duration = Duration(
                value=rhythm.value,
                isDotted=rhythm.dots >= 1,
                tuplet=Tuplet(enters=rhythm.tuplet_numerator, times=rhythm.tuplet_denominator),
            )
        beat.text = bd.text
        beat.octave = bd.octave

        effect = BeatEffect()
        effect.fadeIn = bd.fade_in
        effect.pickStroke = bd.pick_stroke
        effect.slapEffect = bd.slap_effect
        effect.hasRasgueado = bd.has_rasgueado
        effect.vibrato = bd.vibrato
        effect.tremoloBar = bd.whammy
        if bd.brush_direction != BeatStrokeDirection.none:
            effect.stroke = BeatStroke(direction=bd.brush_direction, value=Duration.sixteenth)
        if bd.chord_id and bd.chord_id in td.chords_by_id:
            effect.chord = td.chords_by_id[bd.chord_id]
        beat.effect = effect

        for note_id in bd.note_ids:
            if note_id == _INVALID_ID or note_id not in self._notes_by_id:
                continue
            nd = self._notes_by_id[note_id]
            note = Note(beat)
            note.string = nd.string
            note.value = nd.fret
            note.velocity = bd.velocity
            if nd.is_dead:
                note.type = NoteType.dead
            elif nd.is_tie_destination:
                note.type = NoteType.tie
            else:
                note.type = NoteType.normal

            ne = NoteEffect()
            ne.hammer = nd.is_hammer_origin
            ne.ghostNote = nd.is_ghost
            ne.letRing = nd.is_let_ring
            ne.palmMute = nd.is_palm_mute
            ne.vibrato = nd.is_vibrato
            ne.staccato = nd.is_staccato
            ne.accentuatedNote = nd.accent_normal
            ne.heavyAccentuatedNote = nd.accent_heavy
            ne.leftHandFinger = nd.left_finger
            ne.rightHandFinger = nd.right_finger
            ne.slides = list(nd.slides)
            ne.harmonic = nd.harmonic
            ne.bend = nd.bend
            if nd.trill_fret >= 0:
                ne.trill = TrillEffect(fret=nd.trill_fret, duration=Duration(value=Duration.sixteenth))
            if bd.tremolo_picking is not None:
                ne.tremoloPicking = TremoloPickingEffect(
                    duration=Duration(value=bd.tremolo_picking.duration.value)
                )
            if bd.grace_on_beat is not None:
                ne.grace = GraceEffect(isOnBeat=bd.grace_on_beat)

            note.effect = ne
            beat.notes.append(note)

        beat.status = BeatStatus.normal if beat.notes else BeatStatus.rest
        return beat
