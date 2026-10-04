# dArkOSRE-R36 OTA follow-up — 10032026-r1

Target: R36/R36S on RK3326, after OTA `10032026` (`.VERSION=10032026`).

## Changes

- R36-specific Singe launcher follows the shortcut's `/roms` or `/roms2` root, links both Hypseus shared directories, validates the frame file, and launches either `.singe` scripts or ZLua `.zip` packages. It keeps the R36 `/alg` folder layout and the card selected by EmulationStation.
- Update the Daphne launcher to the R36 source-fork version; it keeps the current R36 texture-stream command.
- Update auto-suspend and settings backup/restore scripts from the maintained R36 source. The backup preserves the previous archive until a new archive succeeds, includes `filebrowser.db` when present, and copies the successful backup to `/roms2` on dual-card systems. Restore pauses NetworkManager and stops FileBrowser while restoring.
- In-place remove the two obsolete Atari 800/XEGS `--config` overrides from their named EmulationStation system blocks. The update verifies that every `<path>` entry is unchanged and both ROM-card switching scripts are identical apart from removal of their obsolete Singe rewrite line.
- Remove the legacy Singe path-rewrite lines from both ROM-card switch scripts. The Singe launcher detects `/roms` versus `/roms2` from the selected shortcut, so global substitutions would otherwise damage its path selection. The rest of both switch scripts is hash-checked unchanged.
- Ensure `/home/ark/.emulationstation/themes` points to `/roms2/themes` only if the path is absent or already a symlink and `/roms2/themes` exists. A real themes directory is preserved.

## Payload and safety

The ZIP contains five scoped scripts only. It contains no ROM trees, `es_systems.cfg`, switch scripts, emulator binaries, libraries, or boot files. The updater detects the active ROM card, stores an owner/mode-preserving rollback tar and checksum under that card's `backup/darkosre-update/10032026-r1`, validates the downloaded ZIP against this SHA-256, and restores the saved paths if a change fails. The generated configuration edit is guarded by an unchanged ROM-path list.

ZIP SHA-256: `12987d5fcc7bd889b922f3e0083b2e454c002b0d7dce6a6c26f192b7ea9b429b`.

## Verification status

The updater passed shell syntax, ZIP path/mode inspection, SHA-256 verification, Atari patch idempotence/path-preservation checks, and the public GitHub Actions archive/shell validation. It installed from the device's `/opt/system/Update.sh` flow and rebooted to active EmulationStation. Post-reboot checks confirmed `.VERSION=10032026-r1`, both ROM cards mounted, all game `<path>` entries still on `/roms2`, the Atari XML parsed, the themes symlink resolved to `/roms2/themes`, switch-script rewrites were absent, and the rollback archive checksum passed. All five installed scripts are root-owned and executable.

No Singe game payload exists under `/roms2/alg`, so Singe/ZLua gameplay was not tested. Daphne gameplay and interactive backup/restore were not tested; the latter were not run to avoid replacing the user's stored backup or settings. Auto-suspend's Python `evdev` import passed, but the user has no `.TIMEOUT` setting so the daemon was not enabled. No Debian upgrade or system Mali/OpenCL link replacement is included. Boot logged `systemd-remount-fs.service` failure (`mount: /: mount point not mounted or bad option`); this OTA does not alter fstab, root mount, kernel, or boot files and this needs separate investigation.

During this OTA the previous updater's hard-coded brightness value 255 exceeded this device's maximum 160 and printed an invalid-argument error; installation still completed. The current raw-main updater now reads `max_brightness` before changing brightness.

Rollback base on a two-card system: `/roms2/backup/darkosre-update/10032026-r1`. From a root shell, restore with:

```sh
B=/roms2/backup/darkosre-update/10032026-r1
while IFS= read -r item; do rm -rf "/$item"; done < "$B/managed-paths.txt"
tar --numeric-owner -xpf "$B/rollback.tar" -C /
```

The device updater has no keyboard confirmation step and reboots after
installation. After startup, run the migration helper from `/roms/tools` or
choose **Update** again. The updated feed then applies the compatibility
package, R2, R3, and R4 in sequence; successful R4 installation requests the
final reboot.
