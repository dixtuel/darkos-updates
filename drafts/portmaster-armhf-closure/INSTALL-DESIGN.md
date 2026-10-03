# Install and recovery design review — 2026-10-03

## Decision

`install_armhf_closure.py` is a separate draft installer with read-only
preflight by default, an explicit `--apply` transaction, and `--resume` from its
backup. It is not wired to the raw updater and has not been applied on the
device. An automatic package-removal rollback is deliberately absent: software
can load a shared object without declaring a dpkg dependency, and removing it
could break that software. The repeatable recovery is to retain the exact
archives and preinstall metadata, leave the update marker unset, and replay
only absent or exact-partial candidates through `--resume`. Never overwrite the
live dpkg status database from a saved snapshot.

## Inputs and evidence

- Package versions, dependencies, archive paths, sizes and hashes:
  `package-manifest.json`.
- The 26 package archives and Debian copyright notices live in the firmware
  source's `resources/third-party/portmaster-legacy-compat/trixie-armhf-dependencies/`.
- Isolated APT simulations used the captured status at
  `build/validation/runtime-followup-20261003/historical-solver/device-status`
  and the independently captured official-base status. Each resolved to 26
  new ARMhf packages, no upgrades and no removals.
- Captured package control data is in
  `build/validation/runtime-followup-20261003/historical-solver/package-control-review.json`.
  All candidates declare `Multi-Arch: same`. No candidate has preinst, prerm,
  or postrm. All request the `ldconfig` trigger. `libgcrypt20` postinst invokes
  stale-library cleanup only when `$2` (the prior version) is nonempty, so it
  does not run that upgrade cleanup on a fresh install. `libvdpau1` declares
  `/etc/vdpau_wrapper.cfg` as a conffile; the exact live file and its dpkg
  ownership must be checked before any future installation.
- Historical solver status SHA256:
  `f5d21b4f4b087088a4f2f3c0a9a0c69544b767290f2ad51c8e2096df3410c2df`.
  The present device may have changed since this snapshot.
- A read-only SSH capture on 2026-10-03 returned that same dpkg status SHA256.
  Primary architecture is `arm64`, `armhf` is enabled as a foreign
  architecture, and `dpkg --audit` returned no output. All 26 corresponding
  installed ARM64 packages are `install ok installed` at exactly the pinned
  versions; the ARMhf package records are absent. The read-only planner reports
  26 candidate additions. This is current device evidence for that capture,
  not a transaction approval.
- Archive review covers all 26 actual `.deb` control/data tar members in
  `archive-review.json`: 372 payload entries, 172 unique non-directory target
  paths, and 55 ARMhf library paths. On the captured device, 32 of the 172
  non-directory paths already exist. All 32 are owned by the same-named ARM64
  package, with content hashes, numeric owner and mode matching the candidate
  archive; none is in `/usr/lib/arm-linux-gnueabihf`. The shared
  `/etc/vdpau_wrapper.cfg` conffile is owned by `libvdpau1:arm64` and matches
  candidate hash
  `938aa62078aef1bced7b85a3dc0d10de6df631b06d23244531553f93b5966378`.
  Detailed device output is in `DEVICE-INVENTORY-2026-10-03.json`.
- The draft installer compares each archive's actual control fields with the
  frozen manifest and archive review; checks all file, symlink and directory
  members; rejects special/traversal members, unreviewed scripts/triggers,
  unknown owners, mismatched bytes/metadata, and noncanonical symlink ancestors.
  It checks `Conflicts`/`Breaks` against installed versions and permits a
  reviewed `Replaces` clause only when the named package has no live dpkg
  record on any architecture; an installed or residual-config record refuses
  the transaction so dpkg cannot take over another package's files.
  The candidate dependency expressions contain only simple comma-separated
  relations; the helper rejects alternatives or unsupported architecture
  qualifiers and checks each dependency against installed ARMhf/`all` packages,
  exact candidates, or an allowed `Multi-Arch: foreign` provider. It never calls
  APT or reads live repositories.

## Required live preflight

1. Capture current `/var/lib/dpkg/status`; record its SHA256, root filesystem
   free space, `.VERSION`, update markers, and `/roms`/`/roms2` mount sources.
   Require `armhf` to be an enabled foreign architecture and the expected R36S
   `arm64` primary architecture. Require `dpkg --audit` to report no broken or
   half-configured packages and ensure no apt/dpkg process is active. The caller
   must serialize updater runs; this helper does not pre-acquire or claim to
   verify dpkg's native lock. The `dpkg --install` child acquires that lock.
2. Re-run the isolated solver from that exact status and the pinned local
   package set. Only the exact 26 requested `name:armhf=version` installs, with
   zero upgrades, removals, replacements, or unresolved dependencies, are
   eligible. Do not use `apt upgrade`, live repositories, or `--force-*`.
3. Classify every package against the current multiarch inventory: absent
   `name:armhf` is a candidate; exact-version, fully installed
   `name:armhf` is retained as already present. Any other state or version is
   a hard stop. Because all 26 packages are `Multi-Arch: same`, if another
   architecture of the same package is installed, its version must exactly
   match the pinned version. Do not replace or downgrade it to make the set
   fit.
4. Inspect each archive's complete data-member list. Reject any existing
   non-directory path unless it is provably the same package's shared
   multiarch conffile at the same package version and the content and dpkg
   ownership match. For `/etc/vdpau_wrapper.cfg`, reject an unknown owner,
   differing content, or differing `libvdpau1` architecture version. Directory
   ancestors may pre-exist only as directories. Run `dpkg -S` against collisions;
   byte equality alone does not establish ownership.
5. Verify each `.deb` SHA256 and declared size against the frozen manifest;
   reject stale or extra archives. Resolve all `Pre-Depends`, `Depends`,
   `Conflicts`, `Breaks`, `Replaces`, `Multi-Arch`, conffiles, maintainer
   scripts, and triggers from the actual archive controls. For reviewed
   `Replaces`, refuse if any replaced package still has a dpkg record (even
   residual config files); do not let dpkg silently take over its files. Never
   infer these properties from filenames or the manifest summary.
6. Confirm the ROM root used by the active EmulationStation paths is unique
   (`/roms` or `/roms2`), and that this exact root is an actually mounted,
   writable card using mount information rather than an `fstab` text match.
   If both roots or neither root occur, or the configured card is not mounted,
   refuse instead of choosing by order. Require enough free space for the
   rollback archive and recovery notes. Save a numeric-owner tar under that card's
   `backup/darkosre-update/<date>-portmaster-armhf-closure/`, including the
   candidate package archives, exact existing shared conffile if any, the
   current dpkg status and package-specific dpkg metadata. Record archive hash,
   status SHA256, active mount source and package decision report. Reject a
   backup path on an unmounted card.
7. Preserve `/roms`, `/roms2`, save paths, SD-switch files, emulator/user
   settings and existing update markers. Do not mark completion before all
   package and affected-loader checks pass. Do not reboot automatically until
   device recovery and normal boot behavior are validated.

## Candidate install transaction, if future evidence closes the gates

Use only the 26 verified local `.deb` files, passed as explicit arguments to a
single dpkg transaction. The helper's default mode is read-only; `--apply` is
required before writes. Do not call APT, `autoremove`, `upgrade`, unpack files
manually, or copy libraries over dpkg-owned paths. Run under the updater's root
context while holding the maintenance lock established by the raw-updater
integration. In addition, the draft helper checks that no package manager
process is active and rechecks the status hash before making a backup or
invoking dpkg. The caller-supplied maintenance lock must remain held through
the operation; dpkg acquires its own package database lock
for the transaction. If a candidate is already installed at its exact version
and fully configured, preserve it and omit it from the dpkg argument list. A
changed, newer, mixed, or noninstalled state is a hard stop. In particular,
installed ARM64 `Multi-Arch: same` peers must match the exact pinned version.
All subprocesses and the dpkg maintainer-script environment receive the
controlled system `PATH` `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`.
Before the backup directory is created, the helper verifies `dpkg`, `dpkg-deb`,
`dpkg-query`, `findmnt`, `ldconfig`, `ps`, `start-stop-daemon`, and `tar` are
available on that path. Missing tools refuse before backup or dpkg.

Before dpkg, the helper matches the active EmulationStation ROM path root to
that root's real writable mount and verifies the card and root have space. It
stores all exact debs, the helper, manifests, dpkg status/log/package metadata,
the prior shared target files, and a numeric-owner/xattr/ACL tar under the
active card's `backup/darkosre-update/portmaster-armhf-closure-*` directory.
This archive is a recovery record; do not extract it over `/` or restore its
dpkg database snapshot.

After dpkg, require all 26 package states to be fully installed at exact
architecture/version and require a clean `dpkg --audit`. If interrupted,
`--resume BACKUP_DIR --apply` validates the stored archives and original
preflight record, then replays only absent or exact-version partial candidate
packages. It checks saved hashes for the helper, package manifest, archive
review, exact `.deb` files, preinstall status, and metadata tar. It refuses
unrelated partial dpkg state and never removes packages.
The caller must leave its marker unset on any failure and run the affected
ARMhf loader plus EmulationStation checks before recording success. This
recovery path is source-reviewed but still needs an isolated interrupted-dpkg
device test before OTA release.

This is a design only. No OTA source code, archive, marker, or raw updater was
changed to perform this transaction.

## Recovery limits and release gate

Before OTA release, test `--apply` and `--resume` in an isolated interrupted
dpkg scenario on the R36S. The candidate set is additive to the captured device
inventory and no package removal is attempted; this does not prove runtime
compatibility or successful recovery on a physical device.

After device preflight and recovery are closed, require the exact OTA ZIP to
pass archive/member/hash/mode and script review, device package-state and loader
verification, reboot/EmulationStation checks, and real PortMaster gameplay
including video, controls, audio, saves, and sustained operation. Label each
claim separately; temporary loader success is not a gameplay result.
