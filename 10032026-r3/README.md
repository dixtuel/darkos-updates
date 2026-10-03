# dArkOSRE-R36 RK3326 runtime follow-up — 10032026-r3

This is the maintained `dixtuel/darkos-updates` feed package for R36S RK3326. The raw updater invokes it only after OTA `10032026-r2` is complete. It is staged in the feed repository locally; it has not been committed or pushed.

## Package

- Archive: `darkosupdate10032026-r3.zip`
- SHA-256: `f6123c9e3a7e95d58b7ca95c7fd653134fac1f5c8236427f2da6637de7755b87` (see `SHA256SUMS`)
- Payload: 19 reviewed files plus the embedded runtime installer. The archive is byte-for-byte copied from the device-tested candidate at `build/validation/ota-review-20261003/runtime-r3-device-candidate.zip`.
- The updater checks RK3326, `.VERSION=10032026-r2`, the R2 completion marker, a uniquely selected mounted ROM card consistent with EmulationStation's paths, the archive checksum and ZIP integrity. It then runs the embedded installer with the archive path and expected SHA-256. Installation rollback stays on the selected ROM card.
- Successful R2 and R3 installer wrappers return the established updater terminal status `187`; nonzero installer errors are passed through unchanged.

## Included changes

The 19 targets cover PPSSPP launch/profile/reset support for both current and 2021 modes, the controller database, BigPEmu launcher handling, performance helper scripts, the Wi-Fi importer/service, EmulationStation nice limit, and guarded zram repair/manager behavior. Exact target paths, hashes and metadata are in the matching draft manifest and payload under `drafts/next-ota-ppsspp-defaults/`.

The controller DB is the repaired R36 source asset (SHA-256 `741a2b21cc85c12c58f1edbe325d610b09fb81d872b9fb3fbb84c4abf86159c5`). The installer accepts the absent database, known original R36 hash `45ce6ad8b8f932ac1cffebd5bb0b23a67ff4813bf9169ec72ba20aef7b278e5d`, or the target hash; it refuses unknown/custom contents before payload writes. This database repair does not by itself change PPSSPP's generic built-in Controls → Restore Defaults mapping. That remaining source/build adaptation is documented in the firmware research report.

The ScreenScraper/TheGamesDB frontend candidate, compatibility-package closure, Debian 13.6 work, emulator binaries beyond this package, and firmware image changes are not included. In particular, this R3 package does not resolve the separate PortMaster ARMhf path-codec loader failure: the device's older R2 lacked `/usr/lib/arm-linux-gnueabihf/libwebpmux.so.3`. A separate guarded26-package ARMhf transaction and absent-only reviewed R2 WebP mux repair subsequently closed all10 native system-path FFmpeg loader checks. The compatibility package is being prepared separately; R3 itself contains none of those additions and is not a PortMaster gameplay test.

## Validation record

The 19-target archive passed the host installer fixtures and the repository OTA validator. The R36S installation used `/roms2`; the device run and post-boot readback verified all 19 targets. The user also confirmed NFS Most Wanted audio and an existing save loaded after launch. These are device outcomes for this exact archive; they do not establish PPSSPP GUI Restore Defaults parity, every game, or unrelated frontend changes.

Repeatable repository checks from the project root:

```sh
python3 repositories/update-fork/10032026-r3/verify-r3-stage.py
(cd repositories/update-fork/10032026-r3 && sha256sum -c SHA256SUMS)
python3 repositories/update-fork/tools/validate-current-ota.py repositories/update-fork/10032026-r3/darkosupdate10032026-r3.zip
bash -n repositories/update-fork/dArkOSUpdate.sh
python3 build/validation/ota-review-20261003/host-fixture.qVuKoL/run-runtime-fixtures.py build/validation/ota-review-20261003/host-fixture.qVuKoL
```

The staged verification helper also checks all 19 source/draft/payload mirrors, archive members and the installer copy; it exercises terminal-marker combinations for base, R1, R2 and R3, and verifies that R2/R3 installer failures retain their status while success maps to `187`. The device installation is already complete, and the updater feed wiring is not public until its repository changes are committed and pushed through the user's release process.
