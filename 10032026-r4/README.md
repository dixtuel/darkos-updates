# dArkOSRE-R36 targeted Advanced SD2 launcher repair — 10032026-r4

This dated raw-updater feed candidate repairs one stale command in the existing Advanced-menu SD2 switcher. It does not replace either switch script, alter EmulationStation paths, install files into `/opt/system/Advanced`, or change ROM/save data.

## Package and order

- Package: `darkosupdate10032026-r4.zip` (one member: `install-r4.py`), SHA-256 is recorded in `SHA256SUMS` and pinned in `dArkOSUpdate.sh`.
- The raw updater requires RK3326, `.VERSION=10032026-r3`, the R3 completion marker, and the separate `10032026-compat` marker. It selects the active ROM card only when its mountpoint and all EmulationStation game paths agree.
- The updater verifies the ZIP SHA-256 and structure before running the installer. After installer success, the R4 marker and `.VERSION` advance and the updater requests the final system reboot. Installer failures retain their nonzero status. If the device is already current, the updater exits without rebooting.
- The installer runs under the shared update-maintenance lock. It snapshots the prior `.VERSION` with numeric ownership and the target file (when present) in a checked tar under the selected ROM card; it preserves `.VERSION` and target owner/mode/xattrs when atomically replacing them. A missing marker with `.VERSION=r4` is a recoverable completed-payload state: the installer revalidates and records the marker on retry.

## Exact change

When `/opt/system/Advanced/Switch to SD2 for Roms.sh` exists, the installer accepts only the pinned official-base or maintained-source pre-fix content hashes, or their exact repaired hashes. It removes the one known `singe.sh` path-rewrite line and verifies the resulting content hash. It preserves numeric UID/GID, mode, and xattrs. Before changing the file, it writes and checks a numeric-owner tar snapshot under `backup/darkosre-update/10032026-r4/` on the actually selected mounted ROM card. Unknown, customized, linked, or non-regular files fail closed.

If that Advanced entry is absent, this OTA does not recreate it. Success is allowed only if `/roms2` is mounted, every EmulationStation path selects `/roms2`, the installed canonical SD2 switcher is the reviewed clean version, and the Main-SD switcher is one of the reviewed variants that regenerates the Advanced SD2 entry from that canonical file. Any other absent-file state fails closed.

Pinned Advanced wrapper hashes:

| State | SHA-256 |
| --- | --- |
| Official base before fix | `64f8cd24996182f1b9a195b8c1bebfae2552e7e19554697b9010df6c6845e6da` |
| Official base after surgical fix | `e6fbeb79127b5f98433d28c1a9eae3df646dbfb46fe97839603b233147ae9f94` |
| Maintained source before source cleanup | `ea3dc01439224d150284966a18e162fcb9fb822cd1c0ff5870a1e36b27e7ac7f` |
| Maintained source after cleanup | `3163fd4f5b34386e2fad15985344711a91e2c01e88810c58b0a03a6d7d7ca4e9` |

The SD2 switch source hash is `3163fd4f5b34386e2fad15985344711a91e2c01e88810c58b0a03a6d7d7ca4e9`. The Main-SD switcher hashes permitted for the safe-absence branch are the device readback `3d4b06b172b36e09d13a44eead165d6752ebf3d3b9ea0bfd2a078bb9a99f59fd` and maintained source `5a0b888bf7263c14a6e525cdcb0005b8f10fbebdcd7f25e0799a1c2e93096684`.

## Validation state

`verify-r4-stage.py` reads the exact official-base script and the pre-fix source bytes from firmware commit `1dd1255`, then exercises both pinned SHA paths, metadata preservation, idempotence, unknown-file refusal, safe-absence/no-create behavior, marker selection and success/failure status mapping under temporary directories. It does not touch device paths.

Both installer branches now have physical R36S evidence dated 2026-10-04. The SD2 safe-absence/no-op run preserved the absent Advanced entry and selected `/roms2`. A follow-up test temporarily selected `/roms` while both card mounts remained active, installed the exact pinned pre-fix wrapper, verified the surgical repair hash and `/roms/backup` rollback archive, then restored the original `/roms2` state. Test method and hashes are recorded in the [R4 ROM-routing validation note](https://github.com/dixtuel/dArkOSRE-R36/blob/main/resources/validation/r4-sd1-rom-routing-20261004.md). These tests validate the R4 installer paths; they do not constitute a clean-image boot test or an end-to-end migration from an older release.
