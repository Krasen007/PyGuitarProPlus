import copy
import io
import zipfile
from pathlib import Path

import pytest

import guitarpro as gp
from guitarpro.format import FormatDetectionError, get_registered_formats
from guitarpro.gpif.gp6_container import GPXReadError, read_gpx, write_gpx
from guitarpro.gpif.gp7_container import GP7ReadError, read_gp7, write_gp7
from guitarpro.gpif.gpif_parser import GpifParseError, GpifParser
from guitarpro.gpif.gpif_writer import GpifWriter

LOCATION = Path(__file__).parent

LOCAL_GPX_FIXTURES = [
    'Armin van Buuren - In And Out Of Love (ver 2).gpx',
    'Armin van Buuren - In And Out Of Love (ver 3 by Adrimor).gpx',
]
LOCAL_GP5_FIXTURE = 'Armin van Buuren - In And Out Of Love (ver 4 by Krasen).gp5'


def _count_song_stats(song: gp.Song) -> tuple[int, int, int, int]:
    tracks = len(song.tracks)
    measures = len(song.measureHeaders)
    non_empty_beats = sum(
        1
        for t in song.tracks
        for m in t.measures
        for v in m.voices
        for b in v.beats
        if b.notes
    )
    notes = sum(
        len(b.notes)
        for t in song.tracks
        for m in t.measures
        for v in m.voices
        for b in v.beats
    )
    return tracks, measures, non_empty_beats, notes


# ---------------------------------------------------------------------------
# 1. Container tests (GP6 BCFZ/BCFS and GP7/GP8 ZIP)
# ---------------------------------------------------------------------------


def test_gpx_container_bcfs_and_bcfz_roundtrip():
    payload = {
        'score.gpif': b'<GPIF><Score><Title>Test</Title></Score></GPIF>',
        'misc.xml': b'<MISC/>',
    }

    for compress in (False, True):
        buf = io.BytesIO()
        write_gpx(payload, buf, compress=compress)
        magic = buf.getvalue()[:4]
        assert magic == (b'BCFZ' if compress else b'BCFS')
        buf.seek(0)
        extracted = read_gpx(buf)
        assert extracted == payload


def test_gpx_container_invalid_header():
    with pytest.raises(GPXReadError):
        read_gpx(io.BytesIO(b'NOPE1234'))


def test_gp7_container_roundtrip_and_invalid():
    payload = {
        'VERSION': b'7.0',
        'Content/score.gpif': b'<GPIF/>',
        'Content/BinaryStylesheet': b'\x01\x02\x03',
    }
    buf = io.BytesIO()
    write_gp7(payload, buf)
    assert buf.getvalue()[:4] == b'PK\x03\x04'
    buf.seek(0)
    assert read_gp7(buf) == payload

    with pytest.raises(GP7ReadError):
        read_gp7(io.BytesIO(b'not-a-zip'))


# ---------------------------------------------------------------------------
# 2. Format detection, registry, and override API tests
# ---------------------------------------------------------------------------


def test_format_registry_contains_all_formats():
    registry = get_registered_formats()
    for fmt in gp.GuitarProFormat:
        assert fmt in registry


@pytest.mark.parametrize(
    'filename, expected_fmt',
    [
        ('Effects.gp3', gp.GuitarProFormat.GP3),
        ('Effects.gp4', gp.GuitarProFormat.GP4),
        ('Effects.gp5', gp.GuitarProFormat.GP5),
    ],
)
def test_detect_format_magic_bytes_legacy(filename, expected_fmt):
    fmt, version = gp.detect_format(LOCATION / filename)
    assert fmt == expected_fmt
    assert version is not None


def test_detect_format_magic_bytes_gp6_gp7_gp8():
    # BCFZ & BCFS
    for compress in (True, False):
        buf = io.BytesIO()
        write_gpx({'score.gpif': b'<GPIF/>'}, buf, compress=compress)
        buf.seek(0)
        fmt, ver = gp.detect_format(buf)
        assert fmt == gp.GuitarProFormat.GP6
        assert ver == (6, 0, 0)

    # ZIP GP7
    buf7 = io.BytesIO()
    write_gp7({'VERSION': b'7.0', 'Content/score.gpif': b'<GPIF><GPVersion>7</GPVersion></GPIF>'}, buf7)
    buf7.seek(0)
    assert gp.detect_format(buf7) == (gp.GuitarProFormat.GP7, (7, 0, 0))

    # ZIP GP8
    buf8 = io.BytesIO()
    write_gp7({'VERSION': b'8.0', 'Content/score.gpif': b'<GPIF><GPVersion>8</GPVersion></GPIF>'}, buf8)
    buf8.seek(0)
    assert gp.detect_format(buf8) == (gp.GuitarProFormat.GP8, (8, 0, 0))


@pytest.mark.parametrize(
    'ext, expected_fmt',
    [
        ('.gp3', gp.GuitarProFormat.GP3),
        ('.gp4', gp.GuitarProFormat.GP4),
        ('.gp5', gp.GuitarProFormat.GP5),
        ('.gpx', gp.GuitarProFormat.GP6),
        ('.gp', gp.GuitarProFormat.GP7),
    ],
)
def test_detect_format_extension_fallback(ext, expected_fmt):
    stream = io.BytesIO(b'\x00\x00\x00\x00unknown-magic')
    stream.name = f'dummy{ext}'
    fmt, _ = gp.detect_format(stream)
    assert fmt == expected_fmt


def test_detect_format_unknown_raises():
    with pytest.raises(FormatDetectionError):
        gp.detect_format(io.BytesIO(b'\x00\x01\x02\x03'), filename='unknown.xyz')

    with pytest.raises(gp.GPException):
        gp.detect_format(io.BytesIO(b''))


def test_explicit_format_override_read_and_write(tmp_path):
    song = gp.parse(LOCATION / 'Effects.gp5')
    # Write as GP6 even with a custom extension, then read back with explicit format=
    custom_path = tmp_path / 'custom.bin'
    gp.write(song, custom_path, format=gp.GuitarProFormat.GP6)
    reparsed = gp.parse(custom_path, format=gp.GuitarProFormat.GP6)
    assert reparsed.versionTuple == (6, 0, 0)
    assert len(reparsed.tracks) == len(song.tracks)
    assert len(reparsed.measureHeaders) == len(song.measureHeaders)


# ---------------------------------------------------------------------------
# 3. GPIF parser/writer unit tests (metadata, structure, effects, extras)
# ---------------------------------------------------------------------------


SAMPLE_GPIF = b"""<?xml version="1.0" encoding="utf-8"?>
<GPIF>
  <GPVersion>7</GPVersion>
  <GPRevision>10000</GPRevision>
  <Encoding><EncodingDescription>GP7</EncodingDescription></Encoding>
  <Score>
    <Title>Unit Test Song</Title>
    <Artist>Tester</Artist>
    <Album>Test Album</Album>
    <Words>Lyricist</Words>
    <Music>Composer</Music>
    <Copyright>2026</Copyright>
    <Tabber>Tab Author</Tabber>
    <Notices>Line 1\nLine 2</Notices>
  </Score>
  <MasterTrack>
    <Tracks>0</Tracks>
    <Automations>
      <Automation>
        <Type>Tempo</Type>
        <Linear>false</Linear>
        <Bar>0</Bar>
        <Position>0</Position>
        <Visible>true</Visible>
        <Value>142 2</Value>
      </Automation>
    </Automations>
  </MasterTrack>
  <Tracks>
    <Track id="0">
      <Name>Lead Guitar</Name>
      <Color>10 20 30</Color>
      <GeneralMidi>
        <Program>29</Program>
        <Port>1</Port>
        <PrimaryChannel>0</PrimaryChannel>
        <SecondaryChannel>1</SecondaryChannel>
      </GeneralMidi>
      <Properties>
        <Property name="CapoFret"><Fret>2</Fret></Property>
        <Property name="Tuning"><Pitches>40 45 50 55 59 64</Pitches></Property>
        <Property name="DiagramCollection">
          <Items>
            <Item id="c0" name="Am">
              <Diagram stringCount="6" baseFret="0">
                <Fret string="0" fret="0"/>
                <Fret string="1" fret="1"/>
                <Fret string="2" fret="2"/>
                <Fret string="3" fret="2"/>
                <Fret string="4" fret="0"/>
              </Diagram>
            </Item>
          </Items>
        </Property>
      </Properties>
      <RSE><ChannelStrip version="E56"><Parameters>0.5 0.5</Parameters></ChannelStrip></RSE>
    </Track>
  </Tracks>
  <MasterBars>
    <MasterBar>
      <Time>3/4</Time>
      <Key><AccidentalCount>1</AccidentalCount><Mode>Major</Mode></Key>
      <Repeat start="true" end="true" count="2"/>
      <AlternateEndings>1</AlternateEndings>
      <Section><Text>Intro</Text></Section>
      <TripletFeel>Triplet8th</TripletFeel>
      <Bars>0</Bars>
    </MasterBar>
  </MasterBars>
  <Bars>
    <Bar id="0"><Voices>0 -1</Voices></Bar>
  </Bars>
  <Voices>
    <Voice id="0"><Beats>0 1</Beats></Voice>
  </Voices>
  <Beats>
    <Beat id="0">
      <Notes>0 1</Notes>
      <Rhythm ref="0"/>
      <FreeText>Let ring!</FreeText>
      <Chord>c0</Chord>
      <Dynamic>FF</Dynamic>
      <Tremolo>1/4</Tremolo>
      <GraceNotes>BeforeBeat</GraceNotes>
      <Properties>
        <Property name="Brush"><Direction>Down</Direction></Property>
        <Property name="PickStroke"><Direction>Up</Direction></Property>
      </Properties>
    </Beat>
    <Beat id="1">
      <Notes>2</Notes>
      <Rhythm ref="1"/>
    </Beat>
  </Beats>
  <Notes>
    <Note id="0">
      <LetRing/>
      <Trill>7</Trill>
      <Accent>8</Accent>
      <Vibrato>Slight</Vibrato>
      <LeftFingering>I</LeftFingering>
      <Properties>
        <Property name="String"><String>0</String></Property>
        <Property name="Fret"><Fret>5</Fret></Property>
        <Property name="HopoOrigin"><Enable/></Property>
        <Property name="PalmMuted"><Enable/></Property>
        <Property name="Slide"><Flags>18</Flags></Property>
        <Property name="HarmonicType"><HType>Tap</HType></Property>
        <Property name="HarmonicFret"><HFret>12</HFret></Property>
      </Properties>
    </Note>
    <Note id="1">
      <Properties>
        <Property name="String"><String>1</String></Property>
        <Property name="Fret"><Fret>7</Fret></Property>
        <Property name="Bended"><Enable/></Property>
        <Property name="BendOriginValue"><Float>0</Float></Property>
        <Property name="BendOriginOffset"><Float>0</Float></Property>
        <Property name="BendDestinationValue"><Float>100</Float></Property>
        <Property name="BendDestinationOffset"><Float>100</Float></Property>
      </Properties>
    </Note>
    <Note id="2">
      <Tie destination="true"/>
      <Properties>
        <Property name="String"><String>1</String></Property>
        <Property name="Fret"><Fret>7</Fret></Property>
      </Properties>
    </Note>
  </Notes>
  <Rhythms>
    <Rhythm id="0">
      <NoteValue>Eighth</NoteValue>
      <AugmentationDot count="1"/>
      <PrimaryTuplet num="3" den="2"/>
    </Rhythm>
    <Rhythm id="1">
      <NoteValue>Quarter</NoteValue>
    </Rhythm>
  </Rhythms>
</GPIF>
"""


def test_gpif_parser_and_writer_all_constructs():
    song = GpifParser().parse(SAMPLE_GPIF)
    assert song.title == 'Unit Test Song'
    assert song.artist == 'Tester'
    assert song.tempo == 142
    assert song.notice == ['Line 1', 'Line 2']

    track = song.tracks[0]
    assert track.name == 'Lead Guitar'
    assert track.offset == 2
    assert [s.value for s in track.strings] == [64, 59, 55, 50, 45, 40]
    assert track.channel.instrument == 29

    mh = song.measureHeaders[0]
    assert mh.timeSignature.numerator == 3
    assert mh.timeSignature.denominator.value == 4
    assert mh.keySignature == gp.KeySignature.GMajor
    assert mh.isRepeatOpen is True
    assert mh.repeatClose == 2
    assert mh.repeatAlternative == 1
    assert mh.marker.title == 'Intro'
    assert mh.tripletFeel == gp.TripletFeel.eighth

    b0, b1 = track.measures[0].voices[0].beats
    assert b0.duration.value == gp.Duration.eighth
    assert b0.duration.isDotted is True
    assert (b0.duration.tuplet.enters, b0.duration.tuplet.times) == (3, 2)
    assert b0.text == 'Let ring!'
    assert b0.effect.chord is not None and b0.effect.chord.name == 'Am'
    assert b0.effect.stroke.direction == gp.BeatStrokeDirection.down
    assert b0.effect.pickStroke == gp.BeatStrokeDirection.up

    n0, n1 = b0.notes
    assert n0.effect.hammer is True
    assert n0.effect.letRing is True
    assert n0.effect.palmMute is True
    assert n0.effect.accentuatedNote is True
    assert n0.effect.vibrato is True
    assert n0.effect.leftHandFinger == gp.Fingering.index
    assert n0.effect.trill is not None and n0.effect.trill.fret == 7
    assert n0.effect.tremoloPicking is not None
    assert n0.effect.grace is not None and n0.effect.grace.isOnBeat is False
    assert isinstance(n0.effect.harmonic, gp.TappedHarmonic)
    assert gp.SlideType.legatoSlideTo in n0.effect.slides
    assert gp.SlideType.intoFromBelow in n0.effect.slides

    assert n1.effect.isBend
    assert n1.effect.bend.points[-1].value == 4

    n2 = b1.notes[0]
    assert n2.type == gp.NoteType.tie

    # Typed extras preserved
    assert song.format_extras is not None
    assert len(song.format_extras.automations) == 1
    assert len(song.format_extras.track_rse_xml) == 1

    # Round-trip through GpifWriter
    xml_out = GpifWriter().write(song, target_major_version=7)
    reparsed = GpifParser().parse(xml_out)
    assert reparsed == song
    assert hash(reparsed) == hash(song)


def test_gpif_invalid_xml_raises():
    with pytest.raises(GpifParseError):
        GpifParser().parse(b'<not-closed')
    with pytest.raises(GpifParseError):
        GpifParser().parse(b'<OtherRoot/>')


# ---------------------------------------------------------------------------
# 4. GP8 experimental read/write & detection
# ---------------------------------------------------------------------------


def test_gp8_roundtrip(tmp_path):
    song = GpifParser().parse(SAMPLE_GPIF)
    gp8_path = tmp_path / 'test_gp8.gp'
    gp.write(song, gp8_path, format=gp.GuitarProFormat.GP8)

    fmt, ver = gp.detect_format(gp8_path)
    assert fmt == gp.GuitarProFormat.GP8
    assert ver == (8, 0, 0)

    reparsed = gp.parse(gp8_path)
    assert reparsed.versionTuple == (8, 0, 0)
    assert reparsed == song


# ---------------------------------------------------------------------------
# 5. Local user fixtures & programmatic edit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('filename', LOCAL_GPX_FIXTURES)
def test_local_gpx_fixtures_roundtrip_and_gp7_conversion(tmp_path, filename):
    filepath = LOCATION / filename
    if not filepath.exists():
        pytest.skip(f"Local fixture not present: {filepath}")

    songA = gp.parse(filepath)
    assert songA.versionTuple == (6, 0, 0)
    tracks, measures, non_empty_beats, notes = _count_song_stats(songA)
    assert tracks >= 1
    assert measures > 10
    assert non_empty_beats > 10
    assert notes > 10

    # Write GPX copy and reparse
    gpx_copy = tmp_path / f'{filename}.copy.gpx'
    gp.write(songA, gpx_copy)
    songB = gp.parse(gpx_copy)
    assert _count_song_stats(songB) == (tracks, measures, non_empty_beats, notes)
    assert songA == songB

    # Write GP7 copy and reparse
    gp_copy = tmp_path / f'{filename}.copy.gp'
    gp.write(songA, gp_copy, format=gp.GuitarProFormat.GP7)
    songC = gp.parse(gp_copy)
    assert _count_song_stats(songC) == (tracks, measures, non_empty_beats, notes)
    assert songA == songC


def test_local_gp5_fixture_regression(tmp_path):
    filepath = LOCATION / LOCAL_GP5_FIXTURE
    if not filepath.exists():
        pytest.skip(f"Local fixture not present: {filepath}")

    songA = gp.parse(filepath)
    out = tmp_path / 'copy.gp5'
    gp.write(songA, out)
    songB = gp.parse(out)
    # GP5 writes an empty single-line notice as 0 lines on re-parse
    if songA.notice == [''] and songB.notice == []:
        songA.notice = []
    assert songA == songB


def test_programmatic_edit_persists_on_gpx_copy(tmp_path):
    filepath = LOCATION / LOCAL_GPX_FIXTURES[0]
    if not filepath.exists():
        pytest.skip(f"Local fixture not present: {filepath}")

    song = gp.parse(filepath)
    orig_measure_count = len(song.measureHeaders)

    # Deep-copy measure 0 and append to song + tracks
    new_header = copy.deepcopy(song.measureHeaders[0])
    new_header.number = orig_measure_count + 1
    song.measureHeaders.append(new_header)
    for track in song.tracks:
        cloned_measure = copy.deepcopy(track.measures[0])
        cloned_measure.header = new_header
        cloned_measure.track = track
        track.measures.append(cloned_measure)

    # Edit first non-empty beat/note in track 0
    edited_note = next(
        b.notes[0]
        for m in song.tracks[0].measures
        for v in m.voices
        for b in v.beats
        if b.notes
    )
    edited_note.value = 15
    edited_note.beat.duration.value = gp.Duration.sixteenth

    out_path = tmp_path / 'edited.gpx'
    gp.write(song, out_path)
    reparsed = gp.parse(out_path)

    assert len(reparsed.measureHeaders) == orig_measure_count + 1
    reparsed_note = next(
        b.notes[0]
        for m in reparsed.tracks[0].measures
        for v in m.voices
        for b in v.beats
        if b.notes
    )
    assert reparsed_note.value == 15
    assert reparsed_note.beat.duration.value == gp.Duration.sixteenth
