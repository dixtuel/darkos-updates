# PortMaster ARMhf compatibility closure — 10032026-compat

Standalone package for the maintained R36 dArkOS update feed. It is intended
for RK3326 devices with `.VERSION` `10032026`, `10032026-r1`, `10032026-r2`,
or `10032026-r3`, and the matching OTA completion marker. It is not a vanilla
firmware update and does not run APT.

## Files

- `darkosupdate10032026-compat.zip` contains the exact 26 pinned ARMhf Debian
  archives, their package manifest and actual archive-control/payload review,
  Debian copyright notices, the fail-closed dpkg helper, and the two reviewed
  ARMhf WebP mux paths needed by the R2 FFmpeg object.
- `apply_portmaster_compat.py` is the guarded bootstrap wrapper. The updater
  must fetch and checksum-verify this script and the ZIP, then invoke it while
  holding the caller-supplied maintenance lock (`/run/lock/darkos-update-maintenance.lock`)
  established by the raw-updater integration. The
  updater should download both files into a private temporary directory and
  verify them against `SHA256SUMS`; the wrapper also requires the exact ZIP
  hash, validates its complete member set and package hashes, checks RK3326 and
  the supported `.VERSION`/marker pair, and extracts only regular files into a
  private temporary directory. It runs the package helper's read-only
  preflight before the explicit dpkg apply.
- `SHA256SUMS` contains the ZIP and wrapper hashes.

The wrapper does not write an update marker or `.VERSION`, reboot, remove
packages, restore dpkg metadata, or run loader/game tests. The caller should
set `.update10032026-compat` only after the wrapper succeeds and the separately
required version-specific loader checks pass. For a base/r1 device that is
about to receive R2, the R2 installer must still validate its legacy FFmpeg
objects; for an existing R2/r3 install, validate its 10 existing ARMhf and
ARM64 FFmpeg objects before the compatibility marker is set. Package
completion does not establish PortMaster gameplay.

## Install and recovery behavior

The helper uses one dpkg transaction with the verified local `.deb` files.
It requires exactly matching Multi-Arch peer versions, rejects unknown path
owners and conflicting versions, checks package dependencies and reviewed
maintainer scripts, and makes a numeric-owner/xattr/ACL preinstall backup on
the actually mounted writable ROM card. It performs no upgrades, removals,
`autoremove`, broad package repair, or online repository access.

The WebP mux object is accepted only when absent or already byte/mode/owner
identical to the reviewed object; its SONAME link is accepted only when absent
or the exact relative link. Any differing file, link, owner, mode, or ancestor
type refuses before package changes. A separate numeric-owner tar and state
record for these two paths are kept under the active card's
`backup/darkosre-update/10032026-compat-webpmux/` directory. The package helper
keeps the exact `.deb` files and its dpkg recovery metadata under
`backup/darkosre-update/portmaster-armhf-closure-*`.

If dpkg is interrupted, leave the completion marker unset and use the helper's
`RECOVERY.txt` instructions to replay only originally absent/exact-partial
packages. Do not restore the saved dpkg database or remove packages: another
installed application may load these libraries without declaring a dpkg
dependency. If the WebP step is interrupted, rerun the wrapper with the same
bundle; it reuses the original WebP rollback snapshot and accepts only absent
or exact reviewed target paths. Recovery never changes `.VERSION` or reboots.

## Validation record

In the feed sequence, successful compatibility installation records its
completion marker and continues directly to R2; it does not create a reboot
boundary. The package closure was installed on the R36S separately from this
ZIP. The device record reports 26 new ARMhf package records, no other package-record
changes or removals, clean `dpkg --audit`, and 10/10 main ARMhf/ARM64 FFmpeg
loader checks after the WebP repair. That validates the installed package and
target objects, not execution of this exact bootstrap wrapper or PortMaster
gameplay. See `device-validation/portmaster-armhf-install-20261003.md` in the
firmware workspace when available. This staged feed package has not been
committed or pushed.

The WebP object is copied byte-for-byte from the reviewed R2 package entry
`usr/lib/arm-linux-gnueabihf/libwebpmux.so.3.0.1` (SHA-256
`247b24116480e9323e0c1d4870208aad3412d8b7bf5f4aad5fc3c4c48ed84cfc`, mode
`0644`). The companion `.so.3` is a symlink payload with exact relative target
`libwebpmux.so.3.0.1`. Backup selection follows the unique ROM root in active
EmulationStation `<path>` entries and refuses mixed/unknown paths or a
non-mounted configured card, including when both cards are mounted.

Host checks:

```sh
python3 repositories/update-fork/10032026-compat/apply_portmaster_compat.py \
  repositories/update-fork/10032026-compat/darkosupdate10032026-compat.zip --verify-only
(
  cd repositories/update-fork/10032026-compat
  sha256sum -c SHA256SUMS
)
python3 repositories/update-fork/tools/validate-current-ota.py \
  repositories/update-fork/10032026-compat/darkosupdate10032026-compat.zip
PYTHONDONTWRITEBYTECODE=1 python3 \
  repositories/update-fork/drafts/portmaster-armhf-closure/host-fixture/test_compat_bundle.py
```

## Final bundle physical validation

The exact ZIP/wrapper hashes in SHA256SUMS were invoked on the R36S under the maintenance lock. Both preflights found all26 exact packages already installed; wrapper completed successfully and preserved them. Independent10 native loader checks and dpkg audit passed, then the caller recorded the compatibility marker while retainingR3 and active original ES. Earlier installation proved the absent-package transaction; this final run proves the public bundle's already-installed path. No PortMaster game result is implied.
