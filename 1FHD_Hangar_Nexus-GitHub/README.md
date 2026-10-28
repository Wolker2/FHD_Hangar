# FHD_Hangar — complete sources for Nexus Mods review

All four variants from the uploaded `FHD_Hangar.rar` are included: **HD, FHD, 2K and 4K**. All **24 runtime files** rebuild from editable source with exactly the uploaded SHA-256 hashes. The source package contains no precompiled DAT/GI files, DLL, EXE or SCR.

The mod replaces the backgrounds of the Hangar, GoodsShop and EquipmentShop forms. Existing ModuleInfo identifies author `Prolog_D;` and displays `ver.2`. Metadata, conflicts, image formats, UI values and runtime behavior are preserved. No RSON project is needed: the supplied mod consists of UI configuration and graphics, with no standalone scripts or native library.

## Variants

| Module | Background Size values in Main.dat | Actual GI pixel dimensions | ModuleInfo encoding |
| --- | --- | --- | --- |
| `FHD_HangarHD` | 1280×720 | 1280×720 | CP1251 |
| `FHD_HangarFHD` | 1920×1080 | 1920×1080 | CP1251 |
| `FHD_Hangar2K` | 2560×1440 | **2752×1536** | UTF-16LE with BOM |
| `FHD_Hangar4K` | 3840×2160 | 3840×2160 | UTF-16LE with BOM |

The 2K pixel/UI size difference exists in the upload and is retained. It has not been diagnosed as a rendering defect. Every variant has three backgrounds, two DAT files and ModuleInfo. The metadata declares the other variants as conflicts, including the older `FHD_Hangar` name; enable one variant at a time.

## Source layout

| Path | Purpose |
| --- | --- |
| `source/CFG/Main.json` | Full recovered configuration for all three forms, shared between variants |
| `source/CFG/CacheData.json` | Shared resource tree with an explicit `{variant}` path placeholder |
| `source/variants.json` | Variant names, three UI size overrides per variant, metadata encodings and explicit GI header/layer fields |
| `source/FHD_Hangar*/DATA/FormHangar2/*.png` | All 12 editable, lossless pixel sources |
| `source/FHD_Hangar*/ModuleInfo.txt` | UTF-8 source metadata, preserving original text and newlines |
| `scripts/` | Complete build, DAT codec and PNG/GI codec |
| `tests/test_source.py` | Five automated checks |
| `original-file-sha256.json` | Original hashes for all 24 runtime files |
| `build-verification.json` | Completed checks and limitations |
| `.github/workflows/build.yml` | GitHub build/check workflow for all variants |

The four original Main.dat trees differ only in the Size values of `EquipmentBackground`, `MarketBackground` and `HangarBackground`. The builder applies exactly those three variant settings to one shared source tree. It expands the CacheData module path and emits each ModuleInfo in its original encoding, including BOM and line endings. No configuration values were removed from the supplied forms.

The PNGs are actual build inputs, not redundant previews. They were recovered from the supplied flattened GI pixels; original layered artwork was not provided. Compiled originals and generated installable ZIPs are excluded from this review archive.

## Build and verification

Verified environment on 28 October 2026: Python 3.12.14, zlib 1.3.2 and Pillow 12.3.0. Python 3.10+ and Pillow are sufficient; no game installation, Windows editor or external decompilation is required.

```sh
python3 -m pip install -r requirements.txt
python3 scripts/build.py --strict-original
python3 -m unittest discover -s tests -v
```

The builder writes four separate installable archives under `dist/`:

- `FHD_HangarHD_FROM_SOURCE.zip`
- `FHD_HangarFHD_FROM_SOURCE.zip`
- `FHD_Hangar2K_FROM_SOURCE.zip`
- `FHD_Hangar4K_FROM_SOURCE.zip`

Each contains six files under `Mods/FHD_MODS/<module>/`. The build report records the complete runtime hashes, package hashes, resource audit and tool versions. The delivered GitHub archive contains source files rather than an installed mod.

To build a single variant, add `--variant FHD_HangarFHD` or another module name. For intentional edits, omit `--strict-original`; the report identifies differing original hashes. The hosted GitHub workflow is supplied but was not executed on GitHub during preparation.

Checks cover all 24 original hashes, all 12 local CacheData references, DAT source roundtrips, the exact three shared-config size changes, original metadata encodings, source-only rebuilding in an isolated temporary directory and ZIP contents. The graphics tests exhaust all 65,536 RGB565 color values through PNG conversion and check ARGB8888 samples with transparent RGB values, partial alpha and pixel edits.

## Graphics format

All twelve GIs use type 0 with one pixel layer. Eleven store RGB565; only `FHD_HangarFHD/2EquipmentBackground.gi` uses ARGB8888. The RGB565 sources are RGB PNGs; the builder quantizes edits to the upper 5/6/5 channel bits. Their recovered original samples rebuild exactly. The ARGB8888 source is an RGBA PNG; alpha and RGB bytes, including RGB under zero alpha, are preserved. GI version, bounds, channel masks, reserved fields and layer bounds are explicit in `variants.json`, not embedded as an opaque binary header.

## Dependencies and limits

The source includes the supplied complete form configuration, which also references the game's existing fonts, sounds, styles, buttons and animations. Only the three background aliases per variant are local replacements. Other image aliases are listed in the verification report and depend on the installed game. Their installed availability and compatibility with other form-changing mods have not been verified.

No live game, in-game rendering, layout at different display resolutions, mixed-mod compatibility, antivirus verdict or Nexus moderation approval is claimed. Byte identity establishes faithful recovery of the supplied files.

Input archive SHA-256: `1abfe8b90a20dab77d3959ac1e54aeb3ceb799e31419f6501d7b4a3fc9709345`. All 24 supplied files were extracted successfully and are reproduced. Existing authorship and descriptions are retained; artwork ownership and redistribution permissions were not supplied or independently established.

The independent DAT codec follows format conventions studied in the previously supplied MIT-licensed [rangers-utils](https://github.com/murgesku/rangers-utils). GI type-0 handling was cross-checked with the previously supplied [SRHD-XenoModKit](https://github.com/Xenomorphchyma/SRHD-XenoModKit) format implementation. No third-party executable is bundled.
