# dArkOSRE online update files

This repository contains the dated ZIP payloads and updater script used by the
online update menu in [dixtuel/dArkOSRE-R36](https://github.com/dixtuel/dArkOSRE-R36).
The source firmware repository is the authoritative place for device-specific
scripts and configuration; this repository hosts files downloaded by that
firmware.

## Current contents

The repository mirrors the full upstream `southoz/darkos-updates` history
through `01302026` (latest upstream commit: 2026-03-14) and adds the documented
R36-specific `10032026` package. Existing upstream payloads remain unchanged.
The new package is assembled from RK3326-selected artifacts in vanilla
06072026, 07262026, and 08272026 releases; it does not install a vanilla image
or rewrite R36 ROM-card configuration. See
[`10032026/README.md`](10032026/README.md) for its exact contents, device
checks, limits, and rollback location.

The upstream update repository has no GitHub Actions workflows or GitHub
Releases. This fork validates shell/archive structure on pushes and pull
requests. Pushing a tag named `ota-<MMDDYYYY>` for a commit on `main` publishes
a GitHub Release with the dated ZIP and checksum file; the same ZIP is already
available to devices from the dated directory on raw `main`.

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
