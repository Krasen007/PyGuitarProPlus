# Third Party Notices

## alphaTab

The GPIF parser, writer, and GPX container implementation in `src/guitarpro/gpif/` is derived from alphaTab:

- **Source**: https://github.com/CoderLine/alphaTab
- **Commit**: `639e20efd111789e029839beb6f573603f3f7c34` (2026-11-19)
- **License**: Mozilla Public License 2.0 (MPL-2.0) (`LICENSE.txt` in alphaTab repository)
- **Files derived from alphaTab**:
  - `src/guitarpro/gpif/gp6_container.py` - derived from `GpxFileSystem.ts` and `BitReader.ts`
  - `src/guitarpro/gpif/gpif_parser.py` - derived from `GpifParser.ts`
  - `src/guitarpro/gpif/gpif_writer.py` - derived from `GpifWriter.ts`
  - `src/guitarpro/gpif/gp7_container.py` - ZIP container handling inspired by `Gp7To8Importer.ts` and `Gp7Exporter.ts`

The original alphaTab MPL-2.0 license notice is preserved in all derived files.

### alphaTab License (MPL-2.0)

```
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
```

The full Mozilla Public License 2.0 text is available at: https://www.mozilla.org/en-US/MPL/2.0/

### alphaTab Attribution

alphaTab is created and maintained by Daniel Kuschny (CoderLine).
Original repository: https://github.com/CoderLine/alphaTab
