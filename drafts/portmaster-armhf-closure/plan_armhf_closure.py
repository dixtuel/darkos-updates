#!/usr/bin/env python3
"""Read-only classifier for captured dpkg status vs the pinned ARMhf closure.

This is a host review aid only. It never invokes dpkg/apt and cannot approve an
installation; see INSTALL-DESIGN.md for additional transaction gates.
"""

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "package-manifest.json"


def parse_status(path):
    records = {}
    text = Path(path).read_text(encoding="utf-8", errors="strict")
    for paragraph in text.split("\n\n"):
        fields = {}
        current = None
        for line in paragraph.splitlines():
            if not line:
                continue
            if line[0].isspace():
                if current:
                    fields[current] += "\n" + line
                continue
            if ":" not in line:
                raise ValueError(f"malformed dpkg status line: {line!r}")
            current, value = line.split(":", 1)
            fields[current] = value.lstrip()
        if fields.get("Package") and fields.get("Architecture"):
            key = (fields["Package"], fields["Architecture"])
            if key in records:
                raise ValueError(f"duplicate package record: {key[0]}:{key[1]}")
            records[key] = fields
    return records


def classify(manifest, records):
    adds, keeps, stops = [], [], []
    for item in manifest["new_armhf_packages"]:
        name = item["Package"]
        version = item["Version"]
        armhf = records.get((name, "armhf"))
        if armhf is None:
            adds.append(f"{name}:armhf={version}")
        elif armhf.get("Status") == "install ok installed" and armhf.get("Version") == version:
            keeps.append(f"{name}:armhf={version}")
        else:
            stops.append(
                f"{name}:armhf has Status={armhf.get('Status')!r}, "
                f"Version={armhf.get('Version')!r}; expected installed {version}"
            )

        # Preserved package controls declare Multi-Arch: same for each candidate.
        for (other_name, arch), other in records.items():
            if other_name != name or arch == "armhf":
                continue
            if other.get("Status") != "install ok installed":
                stops.append(
                    f"{name}:{arch} is in state {other.get('Status')!r}; "
                    "multiarch state needs explicit review"
                )
            elif other.get("Version") != version:
                stops.append(
                    f"{name}:{arch}={other.get('Version')} conflicts with "
                    f"Multi-Arch: same candidate {version}"
                )
    return adds, keeps, stops


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", required=True, help="captured dpkg status file")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args()
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        records = parse_status(args.status)
        adds, keeps, stops = classify(manifest, records)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Captured status records: {len(records)}")
    print(f"Pinned ARMhf packages: {len(manifest['new_armhf_packages'])}")
    print(f"Exact installed and retained: {len(keeps)}")
    print(f"Absent and therefore candidate additions: {len(adds)}")
    for package in keeps:
        print(f"KEEP {package}")
    for package in adds:
        print(f"ADD  {package}")
    for reason in stops:
        print(f"STOP {reason}")
    if stops:
        print("RESULT: REJECT; investigate every STOP before further planning")
        return 1
    print("RESULT: state classification only; dependency/collision/rollback gates remain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
