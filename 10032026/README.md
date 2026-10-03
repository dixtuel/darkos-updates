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

The ZIP intentionally contains no `/roms` or `/roms2` tree, `es_systems.cfg`, SD switching script, ROM directory, or launcher that rewrites card paths. The OTA selects the active ROM card by checking whether `/roms2` is mounted, stores rollback copies under that card's `backup/darkosre-update/10032026` directory (or `/roms/backup/...` when the second card is not mounted), and checks hashes of `es_systems.cfg` and both SD switching scripts before and after installation. It aborts and rolls back if those path-defining files change.

Start this update through the device's Update menu. It has no keyboard-entry confirmation and restarts automatically after a successful install.

Archive SHA-256: 59df7021e908336fa8c7aee78c91bbf6beb8debdfada8af3e22588ff4324adba.

## Verification and limits

Before publishing, each included executable/core was checked against the target device's matching dynamic loader. On-device command smoke checks reported PPSSPP 1.20.4, ScummVM 2026.3.0, Hypseus-Singe 2.12.1, and XRoar 1.11; both retrorun variants initialized their RK3326 RGA library. LowResNX and `parallel_n64` passed loader resolution. These checks do not replace game, controller, audio, save, or per-core gameplay testing.

Rollback copies are kept on the active ROM card. As root, set `B=/roms2/backup/darkosre-update/10032026` on the second-card layout or `B=/roms/backup/darkosre-update/10032026` on the single-card layout, then run: `while IFS= read -r item; do rm -rf "/$item"; if grep -Fxq "$item" "$B/existed-paths.txt"; then mkdir -p "/$(dirname "$item")"; cp -a "$B/$item" "/$(dirname "$item")/"; fi; done < "$B/managed-paths.txt"`. Paths listed in `managed-paths.txt` but absent from `existed-paths.txt` were newly installed and are removed by this procedure. This update does not modify the active ROM-card selection.
