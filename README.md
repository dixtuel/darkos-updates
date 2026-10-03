# dArkOSRE online update files

This repository contains the dated ZIP payloads and updater script used by the
online update menu in [dixtuel/dArkOSRE-R36](https://github.com/dixtuel/dArkOSRE-R36).
The source firmware repository is the authoritative place for device-specific
scripts and configuration; this repository hosts files downloaded by that
firmware.

## Current contents

The repository currently mirrors the upstream `southoz/darkos-updates` history
through `01302026` (latest upstream commit: 2026-03-14). The dated payloads are
stored under matching directories, for example
`01302026/darkosupdate01302026.zip`. There are no GitHub Actions workflows or
GitHub Releases in the upstream update repository; its updater downloads the
versioned ZIP files directly from the repository's raw `main` branch.

These existing ZIPs are the upstream dArkOS update payloads. They have not been
repacked or certified as a new dArkOSRE-R36 update. Do not add a payload here
until its target devices, pre-update state, file list, rollback plan, and device
testing are documented. In particular, a vanilla dArkOS package must not be
assumed safe for every dArkOSRE-R36 installation.

## Update flow

1. The firmware's `/opt/system/Update.sh` downloads `dArkOSUpdate.sh` and
   `LICENSE` from this repository's raw `main` branch.
2. `dArkOSUpdate.sh` selects dated ZIP files using per-update marker files in
   `/home/ark/.config/` and extracts the selected payloads to `/`.
3. A successful update records its marker and updates the displayed version.

Because the updater writes into the live root filesystem, update payloads are
release artifacts, not ordinary application data. Review every ZIP entry and
the matching updater code before publishing a new dated payload. Keep package
names and paths consistent with the existing updater until a deliberate,
backward-compatible migration is reviewed.

## Preparing a payload

- Use the exact dated directory and archive naming convention expected by the
  updater.
- Build the ZIP with paths relative to the filesystem root (for example
  `usr/local/bin/example.sh`), never absolute paths or `..` traversal entries.
- Record the target device/chipset, base firmware version, changes, rollback
  procedure, and test result in the update commit or release notes.
- Validate shell syntax and every ZIP before merging. The repository workflow
  performs those structural checks; it does not prove that a package is safe
  or works on hardware.
- Commit the updater and payload together when the updater depends on the new
  package. Do not publish an update from a partially completed commit.

## Repositories

- Firmware source: <https://github.com/dixtuel/dArkOSRE-R36>
- Update files: <https://github.com/dixtuel/darkos-updates>
- Original update source: <https://github.com/southoz/darkos-updates>

The `upstream` Git remote should remain pointed at `southoz/darkos-updates` so
future changes can be compared and intentionally integrated. The `origin`
remote is this maintained fork.

