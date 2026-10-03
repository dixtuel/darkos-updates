# Legacy FFmpeg ARMhf dependency plan (not an active OTA)

Pinned inputs are preserved in firmware fork commit `cf060259334e7fc5f5909e354e9605970ebf9869` under `resources/third-party/portmaster-legacy-compat/trixie-armhf-dependencies/`. 26 archive hashes/versions/dependencies are mirrored here for OTA planning. No dated ZIP or updater step consumes this directory.

Two isolated APT solves against copied official-base and live-device statuses show 26 new ARMhf packages, zero upgrades/removals. The 26 downloaded archives match signed-index hashes and include licensing notices in the firmware fork. Temporary R36S loader checks pass for five main FFmpeg objects in both ABIs, using the staged ARMhf closure + R2 WebP mux. No installed package/library/cache was changed and no actual PortMaster game was tested.

Before packaging: verify each target device's installed versions/architecture and complete dependencies; do not downgrade newer packages to these pins. Design explicit package installation/metadata/rollback behavior, backup to actual mounted active ROM card, preserve enable states and ROM paths, review maintainer scripts (including libgcrypt upgrade-only cleanup), inspect generated ZIP and test OTA/reboot/real games. The dependencies are system libraries and do not belong under either ROM game tree. Firmware image work remains paused.
