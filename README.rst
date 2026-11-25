PyGuitarPro
===========

.. image:: https://img.shields.io/pypi/v/pyguitarpro.svg?style=flat
   :alt: PyPI Package latest release
   :target: https://pypi.org/project/PyGuitarPro/


Introduction
------------

PyGuitarProPlus is a package to read, write and manipulate Guitar Pro files (GP3, GP4, GP5, GP6 ``.gpx``, GP7 ``.gp``, and
experimental GP8 ``.gp``). It builds on the work of PyGuitarPro which initially PyGuitarPro is a Python port of `AlphaTab <https://www.alphatab.net/>`_ which
originally was a Haxe port of `TuxGuitar <https://sourceforge.net/projects/tuxguitar/>`_.

Supported Formats
-----------------

================= ========= ================ ===========================
Format            Extension Read / Write     Notes
================= ========= ================ ===========================
Guitar Pro 3      ``.gp3``  Read / Write     Binary format
Guitar Pro 4      ``.gp4``  Read / Write     Binary format
Guitar Pro 5      ``.gp5``  Read / Write     Binary format
Guitar Pro 6      ``.gpx``  Read / Write     BCFZ/BCFS + GPIF XML
Guitar Pro 7      ``.gp``   Read / Write     ZIP + GPIF XML
Guitar Pro 8      ``.gp``   Read / Write     Experimental (GPIF XML)
Guitar Pro 1/2    ``.gtp``  Unsupported      Not covered by alphaTab
================= ========= ================ ===========================

Format Detection & API
----------------------

.. code-block:: python

   import guitarpro

   # Auto-detect format from magic bytes or extension
   fmt, version = guitarpro.detect_format('song.gpx')
   song = guitarpro.parse('song.gpx')

   # Explicit format or version override
   song = guitarpro.parse('song.gp', format=guitarpro.GuitarProFormat.GP7)
   guitarpro.write(song, 'copy.gpx', format=guitarpro.GuitarProFormat.GP6)
   guitarpro.write(song, 'copy.gp', version=(7, 0, 0))

   # Programmatic edit example
   song.tracks[0].measures[0].voices[0].beats[0].notes[0].value = 5
   guitarpro.write(song, 'edited.gpx')

Format-specific GPIF data that has no direct equivalent in the core model (such as automations, RSE/mixer XML, and
container files) is preserved in the typed ``song.format_extras`` (:class:`guitarpro.GpifExtras`) slot.

Known Limitations
-----------------

- GP6 ``.gpx`` writing uses linear literal-only BCFZ compression (valid and readable, larger than LZ-compressed files).
- Guitar Pro application-level metadata fidelity (e.g. visual layout/RSE binary blobs) is preserved best-effort via
  ``format_extras`` and not guaranteed across format conversions.
- Guitar Pro 1/2 (``.gtp``) files are not supported.
- Guitar Pro 8 (``.gp``) support is experimental due to limited real-world GP8 fixture coverage.

This package helps you achieve several goals you might find yourself yearning to do in a day-to-day tabber life:

- Transpose a track without messing the fingering
- Add the first string to the track without messing the fingering
- Map percussion notes to different values

Reading ``.gp*`` files is as easy as:

.. code-block:: python

   import guitarpro
   curl = guitarpro.parse('Mastodon - Curl of the Burl.gp5')

Writing ``.gp*`` files isn't that hard either:

.. code-block:: python

   guitarpro.write(curl, 'Mastodon - Curl of the Burl 2.gp5')

All objects representing GP entities are hashable and comparable. This gives a great opportunity to apply the *diff*
algorithm to tabs, or even the *diff3* algorithm to merge tablatures.

For those looking to create the best guitar tablature editor in Python, this package is a good place to start.

Examples
--------

Several usage examples are included in the ``/examples`` folder. Feel free to add your own examples or improve existing
ones. Then, submit them via pull request.

To run one of the examples in your local environment, simply:

.. code-block:: sh

   cd PyGuitarPro
   uv run examples/transpose.py --help


Installation
------------

Install PyGuitarPro from PyPI:

.. code-block:: sh

   pip install PyGuitarPro


Documentation
-------------

Package documentation is located at `Read the Docs <https://pyguitarpro.readthedocs.io/>`_.


Development
-----------

Install the development version of PyGuitarPro with `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: sh

   git clone https://github.com/Perlence/PyGuitarPro.git
   cd PyGuitarPro
   uv sync

Run the tests:

.. code-block:: sh

   uv run pytest

Install the `pre-commit hook <https://adamj.eu/tech/2025/05/07/pre-commit-install-uv/>`_:

.. code-block:: sh

   uv run pre-commit install


Licensing
---------

Please see the file called ``LICENSE``.

.. vim: tw=120 cc=121
