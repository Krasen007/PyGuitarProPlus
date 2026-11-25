Quickstart
==========

After the package has been installed, it's ready for hacking.

Reading ``.gp*`` files is as easy as:

.. code-block:: python

   import guitarpro
   demo = guitarpro.parse('Demo v5.gp5')

Writing ``.gp*`` files isn't that hard as well:

.. code-block:: python

   guitarpro.write(demo, 'Demo v5 2.gp5')

All objects representing GP entities are hashable and comparable. This gives the great opportunity to apply *diff*
algorithm to tabs, or even *diff3* algorithm to merge tablatures.

The package is also designed to convert tablatures between formats. To do this, simply change extension of the output
file according to your desired format:

.. code-block:: python

   guitarpro.write(demo, 'Demo v5.gp4')
   guitarpro.write(demo, 'Demo v6.gpx')
   guitarpro.write(demo, 'Demo v7.gp')

You can also inspect or explicitly override the format:

.. code-block:: python

   fmt, version = guitarpro.detect_format('song.gpx')
   song = guitarpro.parse('song.gpx', format=guitarpro.GuitarProFormat.GP6)
   guitarpro.write(song, 'out.gp', format=guitarpro.GuitarProFormat.GP7)

Functions :func:`guitarpro.parse` and :func:`guitarpro.write` support not only filenames, but also file-like object:

.. code-block:: python

   from urllib.request import urlopen
   with urlopen('https://github.com/Perlence/PyGuitarPro/raw/master/tests/Demo%20v5.gp5') as stream:
       demo = guitarpro.parse(stream)

.. note::

   PyGuitarPro supports GP3, GP4, GP5, GP6 (``.gpx``), GP7 (``.gp``), and experimental GP8 (``.gp``) files.
   Guitar Pro 1/2 (``.gtp``) files are not supported.

.. vim: tw=120 cc=121
