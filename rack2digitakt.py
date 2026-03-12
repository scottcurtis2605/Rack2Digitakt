#!/usr/bin/env python3
"""
rack2digitakt.py - Export Ableton Drum Rack samples to Elektron Digitakt folder structure.

Parses an Ableton .als or .adg file (gzipped XML), extracts samples from each
DrumBranchPreset chain, and copies them into per-category subfolders ready for
transfer via Elektron Transfer.
"""

import argparse
import gzip
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export Ableton Drum Rack samples to Elektron Digitakt folder structure."
    )
    parser.add_argument("als_file", help="Path to .als or .adg file")
    parser.add_argument(
        "-o", "--output",
        default="R2D_export",
        help="Output directory (default: ./R2D_export/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be exported without copying files",
    )
    parser.add_argument(
        "--log",
        metavar="FILE",
        help="Write unresolved sample paths to a log file",
    )
    return parser.parse_args()


def sanitize_folder_name(name: str) -> str:
    """Convert a chain name to a safe folder name."""
    # Replace path-unsafe characters with underscores, collapse runs
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    sanitized = sanitized.strip(". ")
    return sanitized if sanitized else "unnamed"


def load_xml(als_path: Path) -> ET.Element:
    """Decompress and parse the gzip-XML .als/.adg file."""
    with gzip.open(als_path, "rb") as f:
        data = f.read()
    return ET.fromstring(data)


def resolve_path(fileref: ET.Element, als_dir: Path) -> Path | None:
    """
    Resolve a FileRef element to an absolute Path.
    Tries absolute Path first, then relative path from the .als directory.
    Returns None if the file cannot be found.
    """
    abs_el = fileref.find("Path")
    rel_el = fileref.find("RelativePath")

    # Try absolute path
    if abs_el is not None:
        p = Path(abs_el.get("Value", ""))
        if p.is_file():
            return p

    # Try relative path from the .als file location
    if rel_el is not None:
        rel_val = rel_el.get("Value", "")
        if rel_val:
            p = als_dir / rel_val
            if p.is_file():
                return p

    return None


def extract_branches(root: ET.Element) -> list[tuple[str, list[ET.Element]]]:
    """
    Find all DrumBranchPreset elements and return a list of
    (branch_name, [MultiSamplePart, ...]) tuples.
    """
    branches = []
    for branch in root.iter("DrumBranchPreset"):
        name_el = branch.find("Name")
        branch_name = name_el.get("Value", "unnamed") if name_el is not None else "unnamed"
        parts = list(branch.iter("MultiSamplePart"))
        branches.append((branch_name, parts))
    return branches


def collect_file_refs(parts: list[ET.Element]) -> list[ET.Element]:
    """Return one FileRef per MultiSamplePart (deduplicated by path value)."""
    seen = set()
    refs = []
    for part in parts:
        fileref = part.find(".//FileRef")
        if fileref is None:
            continue
        path_el = fileref.find("Path")
        key = path_el.get("Value", "") if path_el is not None else ""
        if key and key not in seen:
            seen.add(key)
            refs.append(fileref)
    return refs


def main():
    args = parse_args()
    als_path = Path(args.als_file).resolve()
    output_dir = Path(args.output).resolve()

    if not als_path.is_file():
        print(f"Error: file not found: {als_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing: {als_path.name}")
    try:
        root = load_xml(als_path)
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    als_dir = als_path.parent
    branches = extract_branches(root)

    if not branches:
        print("No DrumBranchPreset elements found. Is this a Drum Rack file?")
        sys.exit(1)

    print(f"Found {len(branches)} chain(s)\n")

    unresolved: list[str] = []
    summary: dict[str, int] = {}

    for branch_name, parts in branches:
        folder_name = sanitize_folder_name(branch_name)
        dest_dir = output_dir / folder_name
        file_refs = collect_file_refs(parts)

        exported = 0
        skipped = 0

        for fileref in file_refs:
            resolved = resolve_path(fileref, als_dir)
            path_el = fileref.find("Path")
            raw_path = path_el.get("Value", "<unknown>") if path_el is not None else "<unknown>"

            if resolved is None:
                print(f"  [WARN] Cannot find: {raw_path}")
                unresolved.append(raw_path)
                skipped += 1
                continue

            dest_file = dest_dir / resolved.name

            if args.dry_run:
                print(f"  [DRY RUN] {folder_name}/{resolved.name}")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                if dest_file.exists():
                    # Avoid overwriting if identical name from different source
                    stem = dest_file.stem
                    suffix = dest_file.suffix
                    counter = 1
                    while dest_file.exists():
                        dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                shutil.copy2(resolved, dest_file)

            exported += 1

        summary[branch_name] = exported
        status = "[DRY RUN] " if args.dry_run else ""
        print(f"  {status}{branch_name}: {exported} sample(s) exported, {skipped} missing")

    print()
    if args.dry_run:
        print("--- Dry run summary ---")
    else:
        print("--- Export summary ---")
        print(f"Output directory: {output_dir}")

    for name, count in summary.items():
        display_name = sanitize_folder_name(name)
        print(f"  {display_name}: {count}")
    total = sum(summary.values())
    print(f"\nTotal: {total} sample(s) across {len(summary)} chain(s)")

    if unresolved:
        print(f"\n{len(unresolved)} unresolved path(s)")
        if args.log:
            log_path = Path(args.log)
            log_path.write_text("\n".join(unresolved) + "\n")
            print(f"Unresolved paths written to: {log_path}")


if __name__ == "__main__":
    main()
