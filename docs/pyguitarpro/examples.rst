Examples
========

This page contains practical examples for common use cases.


Basic File Operations
---------------------

Read and Write
^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   # Read a file
   song = gp.parse('input.gp5')

   # Modify something
   song.title = 'My Version'

   # Write it back
   gp.write(song, 'output.gp5')


Format Detection
^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   # Detect format before parsing
   fmt, version = gp.detect_format('unknown_file.bin')
   print(f'Format: {fmt.value}, Version: {version}')

   # Parse with detected format
   song = gp.parse('unknown_file.bin', format=fmt)


Format Conversion
-----------------

Convert Between Formats
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   # GP5 → GP6
   song = gp.parse('classic.gp5')
   gp.write(song, 'modern.gpx', format=gp.GuitarProFormat.GP6)

   # GP6 → GP7
   song = gp.parse('modern.gpx')
   gp.write(song, 'latest.gp', format=gp.GuitarProFormat.GP7)

   # GP7 → GP8 (experimental)
   song = gp.parse('latest.gp')
   gp.write(song, 'cutting-edge.gp', version=(8, 0, 0))


Batch Conversion
^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp
   from pathlib import Path

   source_dir = Path('gp5_files')
   target_dir = Path('gpx_files')
   target_dir.mkdir(exist_ok=True)

   for gp5_file in source_dir.glob('*.gp5'):
       song = gp.parse(gp5_file)
       target_file = target_dir / f'{gp5_file.stem}.gpx'
       gp.write(song, target_file, format=gp.GuitarProFormat.GP6)
       print(f'Converted: {gp5_file.name} → {target_file.name}')


Song Metadata
-------------

Read Metadata
^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gpx')

   print(f'Title: {song.title}')
   print(f'Artist: {song.artist}')
   print(f'Album: {song.album}')
   print(f'Author: {song.author}')
   print(f'Copyright: {song.copyright}')
   print(f'Tempo: {song.tempo}')
   print(f'Key: {song.key}')
   print(f'Tracks: {len(song.tracks)}')
   print(f'Measures: {len(song.measureHeaders)}')


Update Metadata
^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gp5')

   # Update song info
   song.title = 'My Cover'
   song.artist = 'Your Name'
   song.album = 'Covers Collection'
   song.author = 'Original Composer'
   song.copyright = '2024'
   song.tempo = 120
   song.notice = ['Arranged for solo guitar', 'Standard tuning']

   gp.write(song, 'my_cover.gp5')


Working with Tracks
-------------------

Iterate Over Tracks
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gpx')

   for i, track in enumerate(song.tracks):
       print(f'Track {i + 1}: {track.name}')
       print(f'  Strings: {len(track.strings)}')
       print(f'  Tuning: {[s.value for s in track.strings]}')
       print(f'  Channel: {track.channel.channel}')
       print(f'  Instrument: {track.channel.instrument}')
       print(f'  Measures: {len(track.measures)}')


Add a New Track
^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gp5')

   # Create a new track
   new_track = gp.Track()
   new_track.name = 'Bass'
   new_track.channel = gp.MidiChannel()
   new_track.channel.channel = 1
   new_track.channel.instrument = 33  # Acoustic Bass

   # Set tuning (4-string bass: E A D G)
   new_track.strings = [
       gp.GuitarString(1, 43),  # G
       gp.GuitarString(2, 38),  # D
       gp.GuitarString(3, 33),  # A
       gp.GuitarString(4, 28),  # E
   ]

   # Add empty measures
   for header in song.measureHeaders:
       measure = gp.Measure(header)
       measure.voices = [gp.Voice(measure) for _ in range(2)]
       for voice in measure.voices:
           voice.beats = [gp.Beat(voice)]
       new_track.measures.append(measure)

   song.tracks.append(new_track)
   gp.write(song, 'with_bass.gp5')


Transpose a Track
^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gp5')
   semitones = 2  # Transpose up 2 semitones

   for measure in song.tracks[0].measures:
       for voice in measure.voices:
           for beat in voice.beats:
               for note in beat.notes:
                   note.value += semitones

   gp.write(song, 'transposed.gp5')


Working with Notes and Effects
-------------------------------

Find and Modify Notes
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gpx')
   track = song.tracks[0]

   # Find all notes and change frets above 12 to harmonics
   for measure in track.measures:
       for voice in measure.voices:
           for beat in voice.beats:
               for note in beat.notes:
                   if note.value > 12:
                       note.effect.harmonic = gp.NaturalHarmonic()
                       print(f'Changed note at fret {note.value} to harmonic')

   gp.write(song, 'with_harmonics.gpx')


Add Effects to Notes
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gp5')
   track = song.tracks[0]
   first_beat = track.measures[0].voices[0].beats[0]

   if first_beat.notes:
       note = first_beat.notes[0]

       # Add hammer-on
       note.effect.hammer = True

       # Add vibrato
       note.effect.vibrato = True

       # Add bend (full step = 100 cents = 4 quarter-tones)
       note.effect.bend = gp.BendEffect()
       note.effect.bend.type = gp.BendType.bend
       note.effect.bend.points = [
           gp.BendPoint(0, 0),      # Start at original pitch
           gp.BendPoint(30, 4),     # Bend to full step at 30%
           gp.BendPoint(60, 4),     # Hold
       ]

       # Add slide
       note.effect.slides = [gp.SlideType.legatoSlideTo]

   gp.write(song, 'with_effects.gp5')


GPIF Format Extras
------------------

Access GPIF-Specific Data
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gpx')

   if song.format_extras:
       print(f'GP Version: {song.format_extras.gp_version}')
       print(f'GP Revision: {song.format_extras.gp_revision}')
       print(f'Encoding: {song.format_extras.encoding_description}')

       # Tempo automations
       for auto in song.format_extras.automations:
           print(f'{auto.type} automation at bar {auto.bar}, position {auto.position}: {auto.value}')

       # RSE settings per track
       for track_id, rse_xml in song.format_extras.track_rse_xml:
           print(f'Track {track_id} has RSE settings: {len(rse_xml)} bytes')

       # Container files (GP6/GP7/GP8)
       for filename, content in song.format_extras.container_files:
           print(f'Container file: {filename} ({len(content)} bytes)')


Preserve Format Extras During Conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   # GP6 → GP7 (preserves format_extras)
   song = gp.parse('song.gpx')
   original_extras = song.format_extras

   gp.write(song, 'song.gp', format=gp.GuitarProFormat.GP7)
   song2 = gp.parse('song.gp')

   # format_extras are preserved within GPIF family
   assert song2.format_extras is not None
   print('Format extras preserved!')


Statistics and Analysis
-----------------------

Count Notes
^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song = gp.parse('song.gp5')

   total_notes = 0
   for track in song.tracks:
       track_notes = 0
       for measure in track.measures:
           for voice in measure.voices:
               for beat in voice.beats:
                   track_notes += len(beat.notes)
       print(f'{track.name}: {track_notes} notes')
       total_notes += track_notes

   print(f'Total: {total_notes} notes')


Analyze Effects Usage
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp
   from collections import Counter

   song = gp.parse('song.gpx')
   effects = Counter()

   for track in song.tracks:
       for measure in track.measures:
           for voice in measure.voices:
               for beat in voice.beats:
                   for note in beat.notes:
                       if note.effect.hammer:
                           effects['hammer-on/pull-off'] += 1
                       if note.effect.vibrato:
                           effects['vibrato'] += 1
                       if note.effect.isBend:
                           effects['bend'] += 1
                       if note.effect.slides:
                           effects['slide'] += len(note.effect.slides)
                       if note.effect.harmonic:
                           effects['harmonic'] += 1
                       if note.effect.letRing:
                           effects['let ring'] += 1
                       if note.effect.palmMute:
                           effects['palm mute'] += 1

   print('Effects usage:')
   for effect, count in effects.most_common():
       print(f'  {effect}: {count}')


Error Handling
--------------

Handle Unknown Formats
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   try:
       fmt, version = gp.detect_format('unknown.xyz')
   except gp.FormatDetectionError as e:
       print(f'Cannot detect format: {e}')

   try:
       song = gp.parse('corrupted.gp5')
   except gp.GPException as e:
       print(f'Failed to parse: {e}')


Safe Format Detection
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp
   from pathlib import Path

   def safe_parse(filepath):
       try:
           fmt, version = gp.detect_format(filepath)
           print(f'Detected: {fmt.value} v{version}')

           song = gp.parse(filepath)
           return song
       except gp.FormatDetectionError:
           print(f'Unknown format: {filepath}')
       except gp.GPException as e:
           print(f'Parse error: {e}')
       return None

   song = safe_parse('song.gpx')
   if song:
       print(f'Successfully loaded: {song.title}')


Advanced Use Cases
------------------

Merge Two Songs
^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp
   import copy

   song1 = gp.parse('song1.gp5')
   song2 = gp.parse('song2.gp5')

   # Copy tracks from song2 to song1
   for track in song2.tracks:
       new_track = copy.deepcopy(track)
       song1.tracks.append(new_track)

   gp.write(song1, 'merged.gp5')


Extract Single Track
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp
   import copy

   song = gp.parse('full_band.gp5')

   # Create a new song with only the guitar track
   new_song = copy.deepcopy(song)
   new_song.tracks = [track for track in new_song.tracks if 'Guitar' in track.name]

   gp.write(new_song, 'guitar_only.gp5')


Compare Two Versions
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import guitarpro as gp

   song1 = gp.parse('version1.gp5')
   song2 = gp.parse('version2.gp5')

   # Compare basic properties
   print(f'Tempo changed: {song1.tempo} → {song2.tempo}')
   print(f'Tracks changed: {len(song1.tracks)} → {len(song2.tracks)}')

   # Deep equality check (works because all models are hashable)
   if song1 == song2:
       print('Songs are identical')
   else:
       print('Songs differ')

       # Find differences in tracks
       for i, (t1, t2) in enumerate(zip(song1.tracks, song2.tracks)):
           if t1 != t2:
               print(f'Track {i + 1} differs: {t1.name}')


.. vim: tw=120 cc=121
