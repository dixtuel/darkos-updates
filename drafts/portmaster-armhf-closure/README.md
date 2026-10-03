# Legacy FFmpeg ARMhf dependency closure (design only; not an active OTA)

The 26 pinned ARMhf `.deb` inputs and hashes are mirrored from the firmware
fork's `resources/third-party/portmaster-legacy-compat/trixie-armhf-dependencies/`.
No dated ZIP or raw-updater step consumes them. The historical official-base
and device-status simulations each selected 26 ARMhf additions, zero upgrades,
and zero removals. Those are snapshot results, not a current device preflight.

Temporary R36S loader checks pass for five principal ARMhf FFmpeg objects when
the staged dependency closure and R2 WebP mux are supplied. The clean-base
execution closure and actual PortMaster gameplay are not proven. The device's
older R2 completion marker does not validate the rebuilt R2 archive or these
packages.

`plan_armhf_closure.py` is an offline, read-only classifier for captured
`dpkg` status. `install_armhf_closure.py` is a separate fail-closed draft helper:
by default it audits local `.deb` inputs; `--apply` is required for its local
dpkg transaction, and `--resume` replays exact archives from its preinstall
backup. It is not wired to the raw updater and has not been run on the device.
See `INSTALL-DESIGN.md`, `HOST-REVIEW-2026-10-03.md`, and `host-fixture/` for
the install gates, live metadata snapshot, and package-control findings. A
device transaction, interrupted-transaction recovery, loader/game behavior,
and any OTA packaging remain unverified.

The intended package layer is `/usr/lib/arm-linux-gnueabihf`; libraries do not
belong under `/roms` or `/roms2`. Any eventual backup must select the actual
mounted active card and store a numeric-owner tar under its `backup/` tree.
Firmware image work and broad Debian upgrades remain separate.
