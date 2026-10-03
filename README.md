# dArkOSRE online update files

This repository contains the dated ZIP payloads and updater script used by the
online update menu in [dixtuel/dArkOSRE-R36](https://github.com/dixtuel/dArkOSRE-R36).
The source firmware repository is the authoritative place for device-specific
scripts and configuration; this repository hosts files downloaded by that
firmware.

## Current contents

The repository mirrors the full upstream `southoz/darkos-updates` history
through `01302026` (latest upstream commit: 2026-03-14) and adds documented
R36-specific packages `10032026`, `10032026-r1`, `10032026-r2`, and staged
`10032026-r3`. Existing upstream payloads remain unchanged.
The new package is assembled from RK3326-selected artifacts in vanilla
06072026, 07262026, and 08272026 releases; it does not install a vanilla image
or rewrite R36 ROM-card configuration. See
[`10032026/README.md`](10032026/README.md) for its exact contents, device
checks, limits, and rollback location. The follow-up `10032026-r1` carries
R36-side auto-suspend, backup/restore, Daphne, Atari, and dual-card Singe/ZLua
changes. See [`10032026-r1/README.md`](10032026-r1/README.md) for its exact
payload, ROM-path guards, checksum, and rollback procedure.
The next `10032026-r2` adds DSperate v3.0.0 as an optional third NDS emulator,
the legacy FFmpeg SONAME set, the missing ARMhf WebP mux dependency, and the
RK3326 Mali OpenCL alias correction. It keeps the device's newer AArch64 WebP
mux library. Its installer patches only the NDS emulator selector and four
BaRT labels/handler paths while checking that every ROM path and both SD
switching scripts remain unchanged.
See [`10032026-r2/README.md`](10032026-r2/README.md) for the binary/source
provenance, device checks, limitations, and rollback location.
The `10032026-r3` runtime follow-up applies only after R2 is complete. Its exact
package hash, target scope and device validation are documented in
[`10032026-r3/README.md`](10032026-r3/README.md). The R3 follow-up is staged in
the working tree and has not been committed or pushed.

The upstream update repository has no GitHub Actions workflows or GitHub
Releases. This fork validates shell/archive structure on pushes and pull
requests. Pushing a tag named `ota-<MMDDYYYY>` or `ota-<MMDDYYYY>-rN` for a
commit on `main` publishes a GitHub Release with the matching ZIP and checksum
file; the same ZIP is already available to devices from its versioned directory
on raw `main`.

## Update flow

1. The firmware's `/opt/system/Update.sh` downloads `dArkOSUpdate.sh` and
   `LICENSE` from this repository's raw `main` branch.
2. `dArkOSUpdate.sh` selects dated ZIP files using per-update marker files in
   `/home/ark/.config/` and extracts the selected payloads to `/`.
3. A successful update records its marker and updates the displayed version.
   The R36/R36S `10032026` update is started from the device's Update menu; it
   does not ask the user to type on a keyboard and reboots after installation.
   The `10032026-r1` follow-up requires the base OTA marker/version `10032026`.
   The `10032026-r2` follow-up applies after `10032026` and/or `10032026-r1`.
   The `10032026-r3` follow-up requires completed `10032026-r2` on RK3326.

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
