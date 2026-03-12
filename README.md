# Rack2Digitakt

A Python CLI script that extracts samples from an Ableton Drum Rack and organises them into a folder structure ready for transfer to an Elektron Digitakt via Elektron Transfer.

## Background

### Ableton Drum Rack structure

An Ableton Drum Rack is a device where each pad is called a **chain**. Each chain typically holds a MultiSampler device loaded with a bank of samples mapped across a zone. In a typical sound-design workflow, a macro knob is assigned to sweep through those samples, letting you audition many variations of a kick, snare, or hat without stopping the session.

Ableton Live Set files (`.als`) and device preset files (`.adg`) are gzipped XML documents. Inside the XML, each drum chain is represented by a `DrumBranchPreset` element with a name (e.g. "Kicks", "Snares", "Closed Hats") and a nested `MultiSampler` containing one `MultiSamplePart` per loaded sample. Each part holds a `FileRef` with both the absolute path and a relative path to the sample file on disk.

### The Digitakt workflow

The Elektron Digitakt organises samples in folders on its +Drive. When you load a project, each track can browse a specific folder to select its sample. The natural mapping is one Drum Rack chain per Digitakt folder: all your kick variations in one folder, all your snares in another, and so on. This replicates the macro knob browsing workflow from Ableton, but on hardware.

Transferring samples to the Digitakt is done via the Elektron Transfer application, which expects a folder of audio files for each category.

## What the script does

1. Accepts a path to an `.als` or `.adg` file as a CLI argument.
2. Decompresses and parses the XML.
3. Finds every `DrumBranchPreset` chain in the Drum Rack and reads its name.
4. Collects all sample file paths from the `MultiSamplePart` zones inside each chain, deduplicated.
5. Resolves each path: tries the stored absolute path first, then falls back to the relative path resolved from the location of the source file.
6. Copies the samples into an output folder, with one subfolder per chain name.
7. Warns about any samples it cannot locate rather than stopping.
8. Prints a per-chain and total summary when done.

The output structure looks like this:

```
R2D_export/
    Kicks/
        BassDrum_3.wav
        BD0010.WAV
        ...
    Snares/
        Snare01.wav
        ...
    Closed Hats/
        HH_closed_01.wav
        ...
```

## Requirements

Python 3.10 or later. No third-party dependencies -- only the standard library is used.

## Usage

```bash
# Basic export
python3 rack2digitakt.py my_kit.adg

# Specify a custom output directory
python3 rack2digitakt.py my_kit.adg -o ~/Desktop/digitakt_samples

# Dry run: print what would be exported without copying anything
python3 rack2digitakt.py my_kit.adg --dry-run

# Write unresolved/missing sample paths to a log file
python3 rack2digitakt.py my_kit.adg --log missing.txt
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `als_file` | (required) | Path to the `.als` or `.adg` file |
| `-o`, `--output` | `./R2D_export` | Output directory |
| `--dry-run` | off | Print actions without copying files |
| `--log FILE` | off | Write unresolved sample paths to a file |

## Notes on sample paths

Ableton embeds both an absolute path and a relative path for each sample reference. If you are running the script on the same machine where the Live Set was created, the absolute path will resolve directly. If you have moved the project or are running on a different machine, the script falls back to the relative path, resolved from the location of the source `.als`/`.adg` file. If neither path resolves, the sample is skipped with a warning and optionally logged.

## Digitakt transfer

Once the export is complete, open Elektron Transfer, connect your Digitakt via USB, and drag each subfolder from `R2D_export` into the appropriate location on the +Drive. The folder names from the Drum Rack chains become your +Drive category folders.
