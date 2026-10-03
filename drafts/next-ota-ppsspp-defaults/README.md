# R36 PPSSPP default adaptation — source candidate, 2026-10-03

Upstream: christianhaitian/dArkOS commit `b19a081539e728c1f5460a158f4243a1728435c0` (2026-05-01), full diff reviewed. It removes conflicting device-1 bindings alongside device-10 mappings in RG351MP/G350 defaults and enables `IgnoreBadMemAccess`.

R36 counterpart: `/opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/{controls.ini,ppsspp.ini}`. The original R36 control template contained exactly the same 13 conflicting bindings. Remove device-1 entries only for Up/Down/Left/Right, Square/Triangle, Start, L/R and four analog directions. Preserve all original device-10 mappings, Select combinations, exit, save/load, slot and fast-forward hotkeys. Set only `IgnoreBadMemAccess = True` in the settings template.

This is the template owner under `/opt`; it does not overwrite existing `/roms/psp/ppsspp` or `/roms2/psp/ppsspp` user profiles or saves. SD switchers and game XML are unchanged. The profile is copied by the original launcher/restore flow when needed; the overlay lacks that launcher, so its exact installed flow must be inspected before claiming new defaults are live. A running device with an existing profile will retain it.

Do not copy vanilla RG351MP controls wholesale: R36 has additional Select hotkeys that are preserved here. Do not transplant the multi-version launcher from `596c142b375d32d706b36a11c65c6c8e1c3cdc35` until the installed R36 launcher and 2021 paths are available. `ForceMaxEmulatedFPS = 30` remains unchanged pending that launcher/profile comparison; upstream removed this cap for modern standalone but retained it for 2021.

State: source adaptation only. No physical PSP title/control/save tests or live settings change; no OTA publication. Matching templates are staged under the updater's `drafts/next-ota-ppsspp-defaults/`, outside its raw release feed. Before packaging, inspect both ROM-card flows and the template-copy behavior; apply only `/opt` files with rollback, preserving numeric metadata and all user profiles.

This directory is not a dated OTA, install script or release. `dArkOSUpdate.sh` does not reference it. Do not install it as a user-profile replacement.

## Additional reviewed ES service candidate

The payload also stages `etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf` with `LimitNICE=-20`, taken from vanilla 08272026 OTA rather than its divergent source unit. Preserve the R36 base service; do not assume any FPS benefit. Future installer must back up the new/existing drop-in, set root:root 0644, reload units and validate the effective service/launcher priorities after restart. Device test is pending; raw updater does not consume this draft.


## Superseding device-backed expansion

After actual R36 readback, this draft now includes 15 source targets: PPSSPP modern/2021 default seeds, dynamic two-card launcher and paired reset tool, Wi-Fi importer plus oneshot service/link, ES nice-limit drop-in, ZRam Manager generator and existing-service boot-order repair/helper. It remains a non-installable draft; no dated ZIP or raw feed references it.

The launcher reads `.ini.sdl`: modern `.ini` and `.ini.sdl` both enable IgnoreBadMemAccess and drop the old forced 30 FPS cap, while 2021 seed retains it. Existing profiles are untouched until the user launches/resets; initial 2021 profile migration copies existing settings and saves into a separate tree without deleting the old profile. After separation, profiles and subsequent saves can diverge; migration is initial-only. No real home config directory is replaced. The existing SD switcher's literal substitutions cannot rewrite the new dynamic launcher.

Reset retains A/B-button confirmation and original two-card scope, also covering the new 2021 profile; an unmounted SD2 is skipped. It deletes only configuration INIs/controls after the user's A-button action, not savedata.

R36 r8188eu USB Wi-Fi is WEXT: upstream-only iw detection fails on the real adapter. The importer adds the tested wireless-sysfs + ip-link fallback. RequiresMountsFor=/opt/system/Tools uses the configured Tools mount regardless of card; no credentials are embedded. Do not run a live credential import test over the sole SSH connection.

The old zram service is enabled but inactive with no active swap. Its default systemd dependencies create a swap/sysinit/local-fs ordering cycle and its ExecStop names nonexistent /usr/bin/swapoff. The reviewed full R36 unit removes that cycle using DefaultDependencies=no, modules-load ordering and explicit shutdown ordering; ExecStop uses existing /usr/sbin/swapoff. An attempted After= reset in a drop-in was rejected after testing because dependency lists cannot be cleared that way; no failed drop-in is shipped. Corrected temporary units verified on device with no cycle/error; no actual service was installed or started. Future OTA must replace zram unit only if an existing generated unit is present, preserve enabled state and /etc/zram.conf, and review existing customizations before replacement. Do not enable zram for users who disabled it.

Before releasing: active-card rollback for all replaced/new paths and link state, metadata, no ROM-profile replacement, effective unit/reboot/menu checks, representative PSP modes/controller/save tests, importer no-keyfile startup test and zram swap observation. This draft is not cleared for public installation.

## PSP Minis and SD2 correction (post-batch diff review, 2026-10-03)

The live and source ES system entries invoke ppsspp.sh for both `psp` and `pspminis`. The first adapted guard accepted only `psp`; this unpublished regression was caught by checking every caller and corrected to accept both under either `/roms` or `/roms2`. Both systems intentionally share the selected card's `psp/ppsspp` or `psp/ppsspp-2021` configuration tree, matching R36 behavior. An unmounted SD2 is now rejected before any profile creation/link change. Neither SD-switcher's slash-delimited replacement matches this mount guard or the dynamic profile paths.

Host mocks passed both cards × both systems × modern/2021 and libretro branches, filenames with spaces, shared profile selection, first-2021 save/config migration, reset with SD2 mounted/unmounted and preservation of real home config directories. No emulator binaries, controls, sound or real games were exercised by these mocks. Source/draft equality, all 15 manifest hashes/modes/link targets and changed shell syntax were checked. These do not replace physical gameplay, boot or OTA validation.

Zram replacement is narrowed to the recorded generated unit SHA256 `237d0729fbc1c8ee2a7dfd50740e304e020a8d1d33e21bd2d65e5b2ef3a724d3`; custom units require separate review. The draft has no installer enforcing this yet and must not be published as a ready OTA.

## Small launcher follow-up (2026-10-03)

The draft now has 18 targets. BigPEmu sets the explicit home-link destination, preserves real home configuration directories and refuses unmounted SD2. perfmax/perfnorm resolve fallback launch artwork using the game card, or actual mounted SD2 plus active ES paths when no game argument exists; clean single-card defaults remain /roms. No governor, image delay or emulator gameplay changes are introduced. Fifteen isolated launcher/card fixtures passed; physical launch/display tests and conditional OTA installer integration remain pending.

## Host installer integration follow-up (2026-10-03)

The draft installer is now `install-runtime.sh` for version `10032026-r3`; it is still only staged here and is not referenced by the raw updater. It verifies the ZIP allowlist, paths, modes, symlink target, hashes, installer self-copy, R36 `.VERSION`/base marker, selected mounted ROM card, and unchanged EmulationStation paths and SD-switch scripts. It snapshots the changed target list to the active ROM card before edits, verifies the snapshot checksum, and restores paths on install/reload/reboot-request failure. Existing file owner/group/mode are retained on POSIX filesystems; VFAT/exFAT metadata remains mount policy. It preserves an existing Wi-Fi enablement choice and refuses unknown Wi-Fi/zram customizations.

Zram behavior is now explicit: only the recognized generated unit is replaced; a masked `/dev/null` unit or absent unit is skipped while the rest of the runtime payload proceeds; a recognized but disabled service remains disabled/inactive. `/etc/zram.conf` is not part of the target list. A custom/unrecognized regular unit is refused before payload edits. The installer checks every managed target's parent components for symlinks before creating the rollback snapshot or writing targets.

The repeatable fixture is `build/validation/ota-review-20261003/host-fixture.qVuKoL/run-runtime-fixtures.py`. Its 19-entry source/draft comparison and host runs passed for fresh install, pre-existing disabled Wi-Fi policy, zram custom refusal, absent and masked zram skip, disabled zram policy, `/roms` and `/roms2` selection while both cards are mounted, rollback metadata, payload-parent and rollback-parent symlink refusal, failed daemon reload rollback, and failed reboot-request rollback. It also checks missing, already-correct, and custom PPSSPP database behavior; preservation of user PPSSPP profile/save files, the home configuration directory, ES XML and both SD-switch scripts. Shell syntax, Python fixture syntax and the generated ZIP's embedded allowlist/hash checks passed. Fixture systemd, mount and reboot behavior is mocked; the non-root host run could preserve/assert the fixture's current numeric ownership but did not exercise privileged `chown` or cross-owner tar restoration.

This closes host-fixture coverage only. No device installation, post-reboot systemd validation, PPSSPP gameplay/controller/save test, actual Wi-Fi import test, PortMaster game test, OTA publication, or physical validation is claimed. Keep publication blocked pending the separately assigned device and PPSSPP regression checks and review of the exact final OTA artifact.

## PPSSPP controller database target (2026-10-03)

The draft now has 19 targets. `opt/ppsspp/assets/gamecontrollerdb.txt` is sourced byte-for-byte from the repaired R36 firmware tree (SHA-256 `741a2b21cc85c12c58f1edbe325d610b09fb81d872b9fb3fbb84c4abf86159c5`, mode `0644`). Its actual controller GUID row was captured on the R36, identifies the native 17-button/4-axis device, and avoids the old invalid `rightstick:b17` mapping. The installer accepts only an absent file, the prior generated R36 database SHA-256 `45ce6ad8b8f932ac1cffebd5bb0b23a67ff4813bf9169ec72ba20aef7b278e5d`, or the already-repaired target hash. It refuses custom or unknown content before rollback creation or target edits; existing numeric owner/group/mode are retained. The original and target hashes are mirrored in the shell and Python archive validators.

This data-file repair restores the missing controller identification data. It does not fix PPSSPP's built-in Settings → Controls → Restore Defaults: v1.20.4's generic SDL defaults still output Cross `10-189`, Circle `10-190`, Square `10-191`, Triangle `10-188`, L `10-194`, R `10-195`. The original R36 seed confirmed by the user uses different face and shoulder token assignments. Native reset parity requires a separately built R36-specific PPSSPP source adaptation; do not infer that this DB target solves it or migrate user profiles as a side effect. See `research/vanilla-audit/ppsspp-r36-builtin-defaults-20261003.md`.

The expanded host fixtures cover missing DB install, acceptance of an already-correct DB with unchanged bytes/metadata, and custom DB refusal before writes. Results and the tested archive hash are recorded in `build/validation/ota-review-20261003/host-fixture.qVuKoL/controller-db-host-fixture-results.json`. This remains draft-only: no live device install, gameplay or GUI-reset parity test, OTA publication, or raw updater wiring was performed by the staging worker.

## Physical installation follow-up (root agent)

The 19-target candidate was applied to the user's R36S on 2026-10-03 after preserving the pre-install readback. Candidate ZIP SHA-256 `f6123c9e3a7e95d58b7ca95c7fd653134fac1f5c8236427f2da6637de7755b87`; installer reported success and requested reboot. Rollback path `/roms2/backup/darkosre-update/10032026-r3`. SSH disconnected during reboot; post-boot verification is pending Remote Services reactivation. This supersedes the staging-only statement above for this exact candidate, not for public release readiness. New ES candidate and PortMaster package additions are excluded.
