# PyGuitarPro All-Format Implementation Plan

Repository: `F:\AI\repos\PyGuitarPro`
Baseline: `master` at `624f23c` (`origin/master`)
Goal: turn the local PyGuitarPro fork into a programmatic library for all Guitar Pro formats, using alphaTab's parser as the implementation source for the GPIF-based formats.

The public API may be changed or extended where needed. The existing `parse()` and `write()` calls must keep working as compatibility wrappers, but new format-aware APIs can be added.

## Support matrix

| Format | Extension | Current state | Target | Implementation source |
|---|---|---|---|---|
| Guitar Pro 3 | `.gp3` | read/write | keep and guard | existing `gp3.py` |
| Guitar Pro 4 | `.gp4` | read/write | keep and guard | existing `gp4.py` |
| Guitar Pro 5 | `.gp5` | read/write | keep and guard | existing `gp5.py` |
| Guitar Pro 6 | `.gpx` | unsupported | read/write | copied/port alphaTab GPIF parser + BCFZ/BCFS container |
| Guitar Pro 7 | `.gp` | unsupported | read/write | copied/port alphaTab GPIF parser + ZIP container |
| Guitar Pro 8 | `.gp` | unsupported | read/write, experimental if fixture coverage is limited | GPIF parser + GP8 extensions; PR #58 as reference |
| Guitar Pro 1/2 | `.gtp` | unsupported | optional stretch only | alphaTab has no importer for this; needs separate source/fixtures |

Non-Guitar-Pro formats exposed by alphaTab (MusicXML, CapXML, alphaTex) are not part of this plan unless requested separately.

## Implementation principles

- Copy/port alphaTab's parser faithfully rather than inventing a new GPIF parser.
- Keep PyGuitarPro dependency-free at runtime: no npm/alphaTab runtime dependency.
- Preserve alphaTab MPL-2.0 notices in all copied or derived files.
- Keep PyGuitarPro's existing GP3/GP4/GP5 behavior stable via regression tests.
- Use the existing `Song`/`Track`/`Measure`/`Voice`/`Beat`/`Note` model where it fits; extend the model where GPIF data has no equivalent.
- Make format detection explicit and testable.
- Never overwrite user fixtures; all write tests go to temporary copies.

## Source material

### Primary implementation source

- alphaTab: https://github.com/CoderLine/alphaTab
- Copy/port the current alphaTab GPIF parser and related model readers into this fork.
- Record the exact alphaTab commit SHA used.
- Keep MPL-2.0 headers and add `THIRD_PARTY_NOTICES.md`.

Areas to port from alphaTab:

- GPIF XML reader/parser and its typed intermediate model.
- Guitar Pro 6 `.gpx` archive handling.
- Guitar Pro 7 `.gp` ZIP handling.
- Note/effect mappings used by `GpifParser`.
- Track, staff, master-bar, automation, chord, and rhythm resolution logic.

### Reference PRs

- PR #62: `Add reading and writing of GP6 (.gpx) and GP7 (.gp) files`
  - https://github.com/Perlence/PyGuitarPro/pull/62
  - Use as an integration reference and test pattern.
  - Known caveat: literal-only BCFZ compression; round-trip verified through PyGuitarPro, not Guitar Pro app.
- PR #63: `Translate GP6/GP7 note effects`
  - https://github.com/Perlence/PyGuitarPro/pull/63
  - Use as a mapping reference for effects.
  - Not covered there: bends/whammy, grace notes, trill/tremolo picking, chord diagrams.
- PR #58: `Add GP6/7/8 (GPIF) support`
  - https://github.com/Perlence/PyGuitarPro/pull/58
  - Use as a GP8 and edge-case reference only.

## Local fixtures already copied into the repo

These are user-supplied local fixtures:

- `tests/Armin van Buuren - In And Out Of Love (ver 2).gpx`
- `tests/Armin van Buuren - In And Out Of Love (ver 3 by Adrimor).gpx`
- `tests/Armin van Buuren - In And Out Of Love (ver 4 by Krasen).gp5`

They are local verification inputs. Do not treat them as redistributable upstream test assets without permission.

## Checklist

### 1. Baseline and branch setup

- [ ] Run `uv sync`.
- [ ] Run `uv run pytest` and record the clean baseline.
- [ ] Create branch `feat/all-guitar-pro-formats` from current `master`.
- [ ] Add/read the PR branches:
  - `$env:GIT_MASTER='1'; git remote add knoguchi https://github.com/knoguchi/PyGuitarPro.git`
  - `$env:GIT_MASTER='1'; git fetch knoguchi feature/gpx feature/gpx-effects`
- [ ] Clone or download alphaTab into a temporary directory outside the fork.
- [ ] Record the alphaTab commit SHA and license file path in `THIRD_PARTY_NOTICES.md`.

### 2. Define the new public API

- [ ] Add `GuitarProFormat` enum with GP3, GP4, GP5, GP6, GP7, GP8 values.
- [ ] Add `detect_format(stream)` for magic-byte and extension-based detection.
- [ ] Extend `parse(stream, format=None, version=None)`:
  - auto-detect by default;
  - allow explicit format override;
  - preserve old calls that pass only a path or stream.
- [ ] Extend `write(song, stream, format=None, version=None)`:
  - infer from extension by default;
  - allow explicit format/version override;
  - preserve old GP3/GP4/GP5 calls.
- [ ] Add a format registry so each format has one reader, one writer, and one sniffer.
- [ ] Add a typed extension slot on `Song` for format-specific data that cannot be represented in the core model.
  - Prefer a typed `FormatExtras`/`GpifExtras` dataclass over `dict[str, Any]`.
  - Use it for automations, MIDI connections, layout, RSE/mixer data, chord diagrams, and unsupported effects.
- [ ] Keep all public types typed; do not use `Any`, `cast`, or `# type: ignore` to force compatibility.

### 3. Copy/port alphaTab's GPIF parser

- [ ] Create `src/guitarpro/_alphatab/` for copied/ported parser sources.
- [ ] Copy or faithfully port alphaTab's GPIF parser into Python.
- [ ] Preserve source comments and MPL-2.0 notices on every derived file.
- [ ] Keep the parser's typed intermediate model internal to the package.
- [ ] Build mappers both ways:
  - GPIF document -> `Song`;
  - `Song` + `GpifExtras` -> GPIF document.
- [ ] Add focused unit tests for representative GPIF constructs:
  - score metadata;
  - tracks and staves;
  - rhythm and tuplets;
  - master bars and repeats;
  - voices, beats, notes;
  - effects.
- [ ] Run `uv run pytest`.

### 4. Add GP6 `.gpx` container support

- [ ] Implement BCFZ/BCFS decoding.
- [ ] Implement BCFZ/BCFS writing.
- [ ] Keep the writer linear even if compression is literal-only.
- [ ] Detect `BCFZ` and `BCFS` magic bytes.
- [ ] Extract `score.gpif` and pass it to the copied GPIF parser.
- [ ] Write `score.gpif` back into a valid BCFS archive.
- [ ] Add container-level tests and one full `.gpx` parse-write-parse test.

### 5. Add GP7 `.gp` container support

- [ ] Detect ZIP magic bytes (`PK\x03\x04`).
- [ ] Read `score.gpif` from the ZIP container.
- [ ] Preserve other ZIP entries where practical.
- [ ] Write a valid `.gp` archive with `score.gpif`.
- [ ] Add container-level tests and one full `.gp` parse-write-parse test.

### 6. Extend the core model and effect coverage

- [ ] Map core score data:
  - metadata;
  - tracks, tuning, MIDI channel/program;
  - measure headers, time/key signatures, repeats;
  - voices, beats, durations, tuplets;
  - notes, frets, strings, ties.
- [ ] Map common effects from PR #63:
  - hammer-on/pull-off;
  - slides;
  - harmonics;
  - fingering;
  - accentuation;
  - beat text.
- [ ] Add coverage for:
  - bends/whammy;
  - grace notes;
  - tremolo picking;
  - trills;
  - palm mute;
  - chord diagrams where the existing `Chord` model supports them.
- [ ] Store unmapped GPIF state in typed extras instead of dropping it silently.
- [ ] Add tests at the mapper boundary for each effect family.

### 7. Add GP8 support

- [ ] Inspect PR #58's GP8 GPIF handling and compare it with the copied alphaTab parser.
- [ ] Identify GP8-specific XML differences using any available fixture/reference.
- [ ] Add GP8 to the format enum and registry.
- [ ] Add GP8 detection and read/write dispatch.
- [ ] Mark GP8 as experimental in docs if no real GP8 fixture is available.
- [ ] Add a GP8 parse-write-parse test if a fixture can be obtained.

### 8. Documentation and licensing

- [ ] Update `README.rst` with the full support matrix.
- [ ] Update `docs/pyguitarpro/quickstart.rst` and remove the "GPX out of scope" note.
- [ ] Document the new API:
  - `detect_format()`;
  - explicit `format=` and `version=` usage;
  - typed extras;
  - programmatic edit examples.
- [ ] Add `THIRD_PARTY_NOTICES.md`.
- [ ] Document known limitations:
  - literal-only BCFZ compression;
  - no guarantee of Guitar Pro app-level metadata fidelity;
  - GP1/GP2 not covered by alphaTab;
  - GP8 experimental status if applicable.

### 9. Tests with the copied local fixtures

- [ ] Parse both copied `.gpx` fixtures and report:
  - track count;
  - measure count;
  - non-empty beat count;
  - note count;
  - detected effects.
- [ ] For each `.gpx` fixture:
  - write a `.gpx` copy;
  - reparse it;
  - compare core model equality and counts;
  - write a `.gp` copy;
  - reparse it;
  - compare core model equality and counts.
- [ ] Use the copied `.gp5` fixture as a regression guard:
  - parse;
  - write `.gp5`;
  - reparse;
  - compare equality.
- [ ] Perform one programmatic edit on a temporary GPX copy:
  - parse;
  - deep-copy a measure;
  - change a note fret or duration;
  - write;
  - reparse;
  - confirm the change persisted.
- [ ] Keep user-supplied fixtures local; do not add them to an upstream PR.

### 10. Regression tests for the new API

- [ ] GP3/GP4/GP5 parse-write-parse tests remain unchanged and green.
- [ ] Magic-byte detection tests for GP3/4/5 headers, BCFZ, BCFS, and ZIP.
- [ ] Extension dispatch tests for `.gp3`, `.gp4`, `.gp5`, `.gpx`, `.gp`.
- [ ] Explicit `format=` override test.
- [ ] Invalid/unknown format raises a clear typed exception.
- [ ] Programmatic edit persistence test.
- [ ] Typed extras preservation test.

### 11. Final verification

- [ ] Run `uv run pytest` with no failures.
- [ ] Run available lint/format checks.
- [ ] Run `git status --short` and confirm only intended files changed.
- [ ] Report:
  - support matrix implemented;
  - copied alphaTab commit SHA;
  - test results;
  - real GPX fixture results;
  - known limitations;
  - whether commits were created (only if explicitly requested).

## Acceptance criteria

- `guitarpro.parse()` reads the copied `.gpx`, `.gp`, and existing `.gp3`/`.gp4`/`.gp5` fixtures.
- `guitarpro.write()` writes `.gpx` and `.gp` copies that can be reparsed by the same API.
- Programmatic edits to a parsed GPIF-based score persist after write and reparse.
- Existing GP3/GP4/GP5 tests remain green.
- The public API has explicit, tested format detection and override behavior.
- alphaTab-derived code is attributed and carries its MPL-2.0 notices.
- README/docs describe all supported formats and limitations honestly.
- No commits are created unless explicitly requested.
