# dArkOSRE-R36 EmulationStation status settings — 10032026-r6

## Package and order

- Package: `darkosupdate10032026-r6.zip`; the exact SHA-256 is recorded in `SHA256SUMS` and pinned by `dArkOSUpdate.sh`.
- Requires the maintained R36S/RK3326 R5 state with the base, R1, compatibility, R2, R3, R4, and R5 markers present. The updater detects the one active mounted ROM card from EmulationStation's configured game paths.
- R5 continues directly into R6; R6 is the final stage and requests the only final restart for an R4/R5-to-R6 update session. No keyboard input is required.
- Before replacing anything, the installer verifies its package and all payload hashes, then stores a metadata-preserving rollback archive under `/<active-rom-root>/backup/darkosre-update/10032026-r6/`.

## Changes

Installs the source-pinned R36 EmulationStation candidate built from FCAMOD `351v` commit `74498be31cd016af6a42d00310f876d7256eff52`, preserving the R36-specific volume-control override and `batteryIndicator` theme adaptation. The AArch64 PIE uses R36's `libEGL.so` graphics linkage. The build has both TheGamesDB and ScreenScraper providers enabled with empty compile-time credential values; it embeds no API keys or ScreenScraper developer credentials. ScreenScraper provider visibility is provided, but authenticated scraping still requires valid authorized service credentials and has not been claimed/tested.

Adds the required `network.svg` resource used by the UI's `SHOW NETWORK ICON` setting. Includes the unchanged Font Awesome 4.7 webfont and OFL-1.1 notice needed by the folder/options glyphs. It does not modify ROM lists, user EmulationStation settings, scraper selections/credentials, themes, saves, or game data. Existing `ShowNetworkIndicator` setting defaults on for devices where it has not been set; the switch is in **START → UI SETTINGS → SHOW NETWORK ICON** and controls the Wi-Fi indicator when the device has a `wlan0` IPv4 address.

The automatic suspend option is already supplied by R1 and remains at **START → ADVANCED SETTINGS → Auto Suspend Timeout (mins)**. This package does not change suspend policy or create a timeout by itself.

## Validation and limits

- `validate-current-ota.py` checks archive integrity, member paths, AArch64 ELF identity and the published hash.
- `verify-r6-stage.py` exercises install, idempotent retry, rollback snapshot, bad-hash rejection, and path preservation on isolated `/roms` and `/roms2` fixtures.
- `verify-update-sequence.py` checks R5-to-R6 ordering, a single final restart, retry of interrupted R6 metadata, and no restart when current.
- `verify-backup-retention.py` confirms R6 retains the newest verified rollback and does not remove unrelated/incomplete backups.
- The exact candidate ELF was launched from a temporary `/tmp` runtime on the physical R36S. The user toggled the Wi-Fi indicator off/on and confirmed it disappeared/returned; the temporary frontend exited and the installed R5 frontend/service remained intact. This is UI candidate evidence, not a completed OTA/reboot test.
- This is an RK3326/R36S-only OTA. Physical confirmation is recorded separately; compile/load evidence does not prove all themes, controls, scraper network authentication, or every game list on every card layout.

Rollback: restore the archived files with `tar --numeric-owner --acls --xattrs -xpf rollback.tar -C /`, then restore `.VERSION` and `.update10032026-r5` from the same archive. The R6 completion marker should be removed when rolling back. The archive's SHA-256 is stored beside it.
