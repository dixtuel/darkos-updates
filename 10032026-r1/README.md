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

The package must pass shell syntax checks, ZIP path/mode inspection, checksum verification, and local shell-path assertions before release. The live device uses `/roms2` and its theme symlink already resolves there. The device currently has no Singe game payload under `/roms2/alg`, so actual Singe/ZLua gameplay cannot be claimed from a launcher-only smoke check. No Debian upgrade or system Mali/OpenCL link replacement is included.

Rollback base on a two-card system: `/roms2/backup/darkosre-update/10032026-r1`. From a root shell, restore with:

```sh
B=/roms2/backup/darkosre-update/10032026-r1
while IFS= read -r item; do rm -rf "/$item"; done < "$B/managed-paths.txt"
tar --numeric-owner -xpf "$B/rollback.tar" -C /
```

The device updater has no keyboard confirmation step and reboots after installation.
