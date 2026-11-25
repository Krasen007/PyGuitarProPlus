Quickstart
==========

After the package has been installed, it's ready for hacking.

Basic Usage
-----------

Reading ``.gp*`` files is as easy as:

.. code-block:: python

   import guitarpro
   demo = guitarpro.parse('Demo v5.gp5')

Writing ``.gp*`` files isn't that hard as well:

.. code-block:: python

   guitarpro.write(demo, 'Demo v5 2.gp5')

All objects representing GP entities are hashable and comparable. This gives the great opportunity to apply *diff*
algorithm to tabs, or even *diff3* algorithm to merge tablatures.


Format Detection
----------------

PyGuitarProPlus automatically detects the format from magic bytes and file extensions:

.. code-block:: python

   import guitarpro

   # Auto-detect format and version
   fmt, version = guitarpro.detect_format('song.gpx')
   # Returns: (GuitarProFormat.GP6, (6, 0, 0))

   # Parse with auto-detection
   song = guitarpro.parse('song.gpx')
   print(f'Detected version: {song.versionTuple}')  # (6, 0, 0)

Supported format enum values:

.. code-block:: python

   guitarpro.GuitarProFormat.GP3  # .gp3
   guitarpro.GuitarProFormat.GP4  # .gp4
   guitarpro.GuitarProFormat.GP5  # .gp5
   guitarpro.GuitarProFormat.GP6  # .gpx
   guitarpro.GuitarProFormat.GP7  # .gp
   guitarpro.GuitarProFormat.GP8  # .gp (experimental)


Format Conversion
-----------------

The package is designed to convert tablatures between formats. Simply change the extension or use explicit format
overrides:

.. code-block:: python

   # Conversion by extension
   song = guitarpro.parse('input.gp5')
   guitarpro.write(song, 'output.gp4')   # Convert to GP4
   guitarpro.write(song, 'output.gpx')   # Convert to GP6
   guitarpro.write(song, 'output.gp')    # Convert to GP7

   # Explicit format override (ignores extension)
   guitarpro.write(song, 'output.bin', format=guitarpro.GuitarProFormat.GP6)

   # Explicit version override
   guitarpro.write(song, 'output.gp', version=(8, 0, 0))

Example: convert a GP6 file to GP7:

.. code-block:: python

   song = guitarpro.parse('classic.gpx')
   guitarpro.write(song, 'modern.gp', format=guitarpro.GuitarProFormat.GP7)


Working with GPIF-Based Formats
--------------------------------

GP6, GP7, and GP8 files use GPIF (Guitar Pro Interchange Format), an XML-based format. Format-specific data that has no
direct equivalent in the core model is preserved in ``song.format_extras``:

.. code-block:: python

   song = guitarpro.parse('song.gpx')

   if song.format_extras:
       # Access GPIF-specific data
       print(f'GP Version: {song.format_extras.gp_version}')
       print(f'GP Revision: {song.format_extras.gp_revision}')

       # Tempo/volume automations
       for automation in song.format_extras.automations:
           print(f'{automation.type} at bar {automation.bar}: {automation.value}')

       # RSE (Realistic Sound Engine) settings per track
       for track_id, rse_xml in song.format_extras.track_rse_xml:
           print(f'Track {track_id} RSE: {rse_xml[:100]}...')

       # Additional container files
       for filename, content in song.format_extras.container_files:
           print(f'Extra file: {filename} ({len(content)} bytes)')

The ``format_extras`` data is preserved during write operations within the same format family (GPIF), but may be lost
when converting between binary (GP3/4/5) and GPIF (GP6/7/8) formats.


Programmatic Editing
--------------------

You can programmatically edit songs and persist changes:

.. code-block:: python

   import guitarpro

   song = guitarpro.parse('original.gpx')

   # Modify song metadata
   song.title = 'My Cover Version'
   song.artist = 'Me'

   # Transpose all notes on the first track
   for measure in song.tracks[0].measures:
       for voice in measure.voices:
           for beat in voice.beats:
               for note in beat.notes:
                   note.value += 2  # Move up 2 frets

   # Change tempo
   song.tempo = 140

   # Save changes
   guitarpro.write(song, 'modified.gpx')


Streaming and File-Like Objects
--------------------------------

Functions :func:`guitarpro.parse` and :func:`guitarpro.write` support not only filenames, but also file-like objects:

.. code-block:: python

   from urllib.request import urlopen
   import guitarpro

   # Read from URL
   with urlopen('https://example.com/song.gp5') as stream:
       song = guitarpro.parse(stream)

   # Read from bytes
   from io import BytesIO
   with open('song.gpx', 'rb') as f:
       data = f.read()
   song = guitarpro.parse(BytesIO(data))

   # Write to BytesIO
   buffer = BytesIO()
   guitarpro.write(song, buffer, format=guitarpro.GuitarProFormat.GP7)
   output_bytes = buffer.getvalue()


Format Support Matrix
---------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Format
     - Extension
     - Support
     - Notes
   * - Guitar Pro 3
     - ``.gp3``
     - Read/Write
     - Binary format
   * - Guitar Pro 4
     - ``.gp4``
     - Read/Write
     - Binary format
   * - Guitar Pro 5
     - ``.gp5``
     - Read/Write
     - Binary format
   * - Guitar Pro 6
     - ``.gpx``
     - Read/Write
     - BCFZ/BCFS container + GPIF XML
   * - Guitar Pro 7
     - ``.gp``
     - Read/Write
     - ZIP container + GPIF XML
   * - Guitar Pro 8
     - ``.gp``
     - Read/Write
     - Experimental (limited fixture coverage)
   * - Guitar Pro 1/2
     - ``.gtp``
     - Not supported
     - alphaTab has no importer


Known Limitations
-----------------

- **GP6 compression:** PyGuitarProPlus writes GP6 files using literal-only BCFZ compression. These files are valid and
  readable by Guitar Pro but are larger than files compressed with Guitar Pro's LZ compression.
- **Guitar Pro app metadata:** Visual layout, RSE binary blobs, and other application-level metadata are preserved
  best-effort via ``format_extras`` but are not guaranteed to survive format conversions (especially GP3/4/5 ↔ GP6/7/8).
- **GP8 experimental:** GP8 support is marked experimental due to limited real-world GP8 fixture coverage.
- **GP1/GP2:** Not supported (alphaTab does not provide an importer for these formats).


Next Steps
----------

- Explore the :doc:`api` reference for detailed documentation
- Learn about :doc:`format` internals for GP3/4/5 and GPIF structures
- Check the ``examples/`` folder in the repository for practical usage patterns

.. vim: tw=120 cc=121
