# dArkOSRE-R36 RK3326 OTA — 2026-10-03

Target: dArkOSRE-R36 on RK3326 (including R36S), currently based on `.VERSION` 03082026.

This is a selective, device-targeted update assembled from the RK3326 artifacts in the vanilla dArkOS 06072026, 07262026, and 08272026 update payloads. It does not apply the vanilla firmware image, Debian package upgrades, RK3566 binaries, DSperate, or the upstream EmulationStation configuration.

## Included

- PPSSPP standalone 1.20.4 executable and its matching assets.
- ScummVM 2026.3.0 executable and matching themes/translations.
- Hypseus-Singe 2.12.1 RK3326 executable and its font/image assets.
- XRoar 1.11 executable.
- LowRes NX RetroArch core and core-info file (missing from the inspected device installation).
- RK3326 `parallel_n64` RetroArch32 core.
- RK3326 `retrorun` and `retrorun32` binaries at the paths used by dArkOSRE launchers.
- The maintained firmware updater entrypoint, configured to fetch this fork's `main` branch.

## ROM-card safety

The ZIP intentionally contains no `/roms` or `/roms2` tree, `es_systems.cfg`, SD switching script, ROM directory, or launcher that rewrites card paths. The OTA selects the active ROM card by checking whether `/roms2` is mounted, stores a metadata-preserving `rollback.tar` plus its SHA-256 under that card's `backup/darkosre-update/10032026` directory (or `/roms/backup/...` when the second card is not mounted), and checks hashes of `es_systems.cfg` and both SD switching scripts before and after installation. It aborts and rolls back if those path-defining files change. Storing the rollback as one tar archive keeps Linux ownership and mode metadata even when the ROM card is FAT32/exFAT.

Start this update through the device's Update menu. It has no keyboard-entry confirmation and restarts automatically after a successful install.

Archive SHA-256: 59df7021e908336fa8c7aee78c91bbf6beb8debdfada8af3e22588ff4324adba.

## Verification and limits

Before publishing, each included executable/core was checked against the target device's matching dynamic loader. On-device command smoke checks reported PPSSPP 1.20.4, ScummVM 2026.3.0, Hypseus-Singe 2.12.1, and XRoar 1.11; both retrorun variants initialized their RK3326 RGA library. LowResNX and `parallel_n64` passed loader resolution. These checks do not replace game, controller, audio, save, or per-core gameplay testing.

Rollback data is kept on the active ROM card. As root, set `B=/roms2/backup/darkosre-update/10032026` on the second-card layout or `B=/roms/backup/darkosre-update/10032026` on the single-card layout, then run: `while IFS= read -r item; do rm -rf "/$item"; done < "$B/managed-paths.txt"; tar --numeric-owner -xpf "$B/rollback.tar" -C /`. This removes all update-managed paths and restores the original files, owners, and modes from the archive. This update does not modify the active ROM-card selection.

## R36 controller database correction — 2026-10-03

The original local217-entry package replaced PPSSPP assets but omitted gamecontrollerdb.txt. It was present in the source overlay and previous device assets; losing it selected the wrong SDL built-in mapping and removed guide/stick bindings. The218-entry candidate now includes the reviewed R36 database, with the original GO-Advance row retained, corrected GO-Super rightstick:b15 (17 buttons), and the native SDL2 CRC-aware GUID record. This is R36 adaptation data, not a wholesale vanilla database replacement.

Native SDL lookup and user NFS Most Wanted5-1-0 input test passed with the original R36 controls template: B/Cross, X/Triangle, Y/Square, A/Circle and L/R. FN opens the emulator menu. No userprofile or save is in this ZIP. PPSSPP's own in-app RestoreDefaults uses different compiled mappings and is still a separate adaptation gate. Already-updated devices need a dedicated follow-up delivery; their base marker will skip this rebuilt archive. Candidatehash is in SHA256SUMS; this artifact has not been published or clean-installed.
