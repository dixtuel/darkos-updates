# dArkOSRE-R36 DSperate RK3326 defaults — 10032026-r5

## Package and order

- Package: `darkosupdate10032026-r5.zip`; SHA-256 is in `SHA256SUMS` and pinned in `dArkOSUpdate.sh`.
- Requires an R36S/RK3326 device at R4, with the base, R1, compatibility, R2, R3, and R4 markers complete. The updater resolves the one active ROM card from EmulationStation paths and requires it to be mounted.
- R4 now continues directly into R5. R5 is the only final restart for the R4-to-R5 chain. The package changes DS settings and an Advanced menu script; it does not need an intermediate restart.
- The updater preserves a checked rollback tar on the selected card at `backup/darkosre-update/10032026-r5/`. It includes the global DSperate template, reset tool, selected-card config, version and preceding stage marker. The normal retention logic keeps the newest verified rollback.

## Changes

The package installs the reviewed R36S DSperate defaults into `/opt/DSperate/config/dsperate.ini` and adds `Restore Default DSperate Settings.sh` to `/opt/system/Advanced/`. It merges the R36 RK3326 profile only where a setting is missing. Existing explicit values—including layout, frameskip, and controller preferences—remain intact.

The R36S profile follows vanilla's `DSperate/configs/dsperate.ini.rk3326`: `cpu_oc=false`, `timing_oc=false`, `fast_load=true`; pad hotkeys are `modifier=none`, `quit=start+back`, `pause=guide`, save/load with modifier+R1/L1, next/previous layout with R2/L2, screen swap with L2, and microphone with L3. No firmware or BIOS dump is included; R36S continues to use DSperate's built-in FreeBIOS fallback.

The Advanced tool uses controller A/B through `buttonmon.sh`, resolves `/roms` versus `/roms2` from the actual EmulationStation game paths and mounted card, and resets only the selected card's `nds/dsperate/dsperate.ini`. It writes a single previous-settings copy to `backup/dsperate-restore/dsperate.ini.previous`. DS battery saves, save states, cheats, game files, and per-game overrides are not removed. The tool rewrites only the save/state/cheat paths to the selected ROM card.

## Validation and limits

- `verify-update-sequence.py`: R4-to-R5 ordering, stage markers, one final restart, and current-version no-reboot behavior.
- `verify-r5-stage.py`: isolated R5 install on both `/roms` and `/roms2`, preservation of explicit settings and paths, idempotence, rollback archive, bad checksum refusal.
- `validate-current-ota.py`: ZIP path/CRC/checksum and shell syntax validation.
- Physical R36S launch, DS game controls, microphone, audio, battery save and save-state behavior remain separate gameplay checks; version/config installation does not establish those results.
