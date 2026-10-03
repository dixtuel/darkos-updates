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
