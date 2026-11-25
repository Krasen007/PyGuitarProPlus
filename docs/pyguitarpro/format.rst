Guitar Pro File Formats
=======================

PyGuitarProPlus supports multiple Guitar Pro format families:

- **Binary formats:** GP3, GP4, GP5 (documented below)
- **GPIF-based formats:** GP6 (``.gpx``), GP7 (``.gp``), GP8 (``.gp``)


GPIF-Based Formats (GP6, GP7, GP8)
-----------------------------------

GP6, GP7, and GP8 use GPIF (Guitar Pro Interchange Format), an XML-based format for representing tablature data.

GP6 (``.gpx``)
^^^^^^^^^^^^^^

Guitar Pro 6 files use the ``.gpx`` extension and consist of:

- **Container:** BCFZ (compressed) or BCFS (uncompressed) proprietary archive format
- **Content:** ``score.gpif`` XML file + optional binary resources (RSE, stylesheets, etc.)
- **Compression:** PyGuitarProPlus writes using literal-only BCFZ compression (valid but larger than Guitar Pro's
  LZ-compressed files)

GP7 (``.gp``)
^^^^^^^^^^^^^

Guitar Pro 7 files use the ``.gp`` extension and consist of:

- **Container:** Standard ZIP archive (``PK`` magic bytes)
- **Content:** ``Content/score.gpif`` or ``score.gpif`` XML file + ``VERSION`` file + optional resources
- **Layout:** Preserves additional ZIP entries via ``format_extras.container_files``

GP8 (``.gp``)
^^^^^^^^^^^^^

Guitar Pro 8 files also use the ``.gp`` extension with the same ZIP container as GP7:

- **Detection:** Identified by ``VERSION`` file content (``8.x``) or ``<GPVersion>8</GPVersion>`` in GPIF XML
- **Status:** Experimental due to limited real-world GP8 fixture coverage
- **Compatibility:** Uses the same read/write pipeline as GP7 with version-aware serialization

GPIF XML Structure
^^^^^^^^^^^^^^^^^^

The GPIF format represents:

- Score metadata (title, artist, album, copyright, etc.)
- Master track with tempo automations
- Tracks with tuning, MIDI settings, and RSE configuration
- Master bars (global measure properties: time signature, key, repeats, sections)
- Bars, voices, beats, notes with full effect data
- Rhythms (durations, tuplets, dotted notes)
- Chord diagrams

**Preserved via** ``GpifExtras``:

- Automations (tempo, volume curves)
- RSE/mixer XML per track
- Track sounds and automations
- Container files (BinaryStylesheet, etc.)


Basic Guitar Pro 3–5 types
--------------------------

.. _byte:

Byte
^^^^

Values of type :ref:`byte` are stored in 1 byte.


.. _signed-byte:

Signed byte
^^^^^^^^^^^

Values of type :ref:`signed-byte` are stored in 1 byte.


.. _bool:

Bool
^^^^

Values of type :ref:`bool` are stored in 1 byte.


.. _short:

Short
^^^^^

Values of type :ref:`short` are stored in 2 little-endian bytes.


.. _int:

Int
^^^

Values of type :ref:`int` are stored in 4 little-endian bytes.


.. _float:

Float
^^^^^

Values of type :ref:`float` are stored in 4 little-endian bytes.


.. _double:

Double
^^^^^^

Values of type :ref:`double` are stored in 8 little-endian bytes.


.. _byte-size-string:

ByteSizeString
^^^^^^^^^^^^^^

Values of type :ref:`byte-size-string` are represented by length of the string (1 :ref:`byte`) followed by characters
encoded in an 8-bit charset.


.. _int-size-string:

IntSizeString
^^^^^^^^^^^^^

Values of type :ref:`int-size-string` are represented by length of the string (1 :ref:`int`) followed by characters
encoded in an 8-bit charset.


.. _int-byte-size-string:

IntByteSizeString
^^^^^^^^^^^^^^^^^

Values of type :ref:`int-byte-size-string` are represented by an :ref:`int` holding length of the string increased by 1,
a :ref:`byte` holding length of the string and finally followed by characters encoded in an 8-bit charset.


Guitar Pro 3 format
-------------------


.. automodule:: guitarpro.gp3
   :members:


Guitar Pro 4 format
-------------------

.. automodule:: guitarpro.gp4
   :members:


Guitar Pro 5 format
-------------------

.. automodule:: guitarpro.gp5
   :members:

.. vim: tw=120 cc=121
