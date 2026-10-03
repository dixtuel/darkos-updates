# ARMhf package planner review — 2026-10-03

The review helper is intentionally read-only: `plan_armhf_closure.py` reads a
captured dpkg status and the pinned manifest, then reports exact installed
packages, absent package candidates, and hard stops. It has no dpkg or APT
calls. A small host fixture exercises absent/exact/mismatch/multiarch/partial
states in `host-fixture/fixtures.json`.

Historical captured status:

- Input:
  `build/validation/runtime-followup-20261003/historical-solver/device-status`
- SHA256:
  `f5d21b4f4b087088a4f2f3c0a9a0c69544b767290f2ad51c8e2096df3410c2df`
- The associated simulation selected 26 new ARMhf packages with zero upgrades
  and zero removals.
- The status classifier sees 26 absent ARMhf package records in that historical
  snapshot. Do not treat this as a fresh query of the handheld.

Fresh read-only device capture (SSH, 2026-10-03):

- Primary architecture `arm64`; foreign architecture `armhf`; `dpkg --audit`
  returned no output.
- Fresh `/var/lib/dpkg/status` SHA256 is the same
  `f5d21b4f4b087088a4f2f3c0a9a0c69544b767290f2ad51c8e2096df3410c2df`.
- All 26 ARM64 counterparts are installed at the exact candidate versions; all
  ARMhf package records are absent. Planner output: 26 candidates, no status
  conflicts. This only confirms package-state classification.
- The actual archive review enumerates 372 data entries and 172 unique
  non-directory targets. Of the 172, 32 already exist and are all owned by the
  same-name ARM64 packages. Content hashes, numeric owners and modes match the
  pinned archives for every existing path. No ARMhf library target currently
  exists in `/usr/lib/arm-linux-gnueabihf`. `/etc/vdpau_wrapper.cfg` is owned
  by `libvdpau1:arm64` and exactly matches the ARMhf archive conffile hash.
- Package states, library targets and 32 existing-path metadata are summarized
  in `DEVICE-INVENTORY-2026-10-03.json`. The raw status capture was not added
  to the repository.
- A second read-only check at 2026-10-03 21:31 TRT confirmed that status hash,
  architecture, enabled foreign architecture, clean `dpkg --audit`, all 26
  absent ARMhf candidates, and exact ARM64 peers are unchanged. Both cards are
  mounted read/write: `/roms2` is `/dev/mmcblk1p1` (vfat), and `/roms` is
  `/dev/mmcblk0p3` (exfat). The conffile hash/owner is unchanged. All ten
  package names referenced by reviewed `Conflicts`/`Replaces` clauses have no
  live dpkg record. See the `read_only_followup_capture` object in the JSON
  inventory for the compact result.

Package control review:

- All 26 packages declare `Multi-Arch: same`. A planner/runtime preflight must
  compare same-named packages across every installed architecture and reject
  differing versions rather than allow replacement/downgrade.
- Only `libgcrypt20` has a maintainer script (`postinst`). It runs stale shared
  library cleanup only when an old version is passed; fresh install has no
  old-version argument. All candidates request `ldconfig`; no candidate has
  preinst, prerm, or postrm.
- `libvdpau1` has the shared `/etc/vdpau_wrapper.cfg` conffile. Its existence,
  content, ownership and cross-architecture package version must be checked on
  target. A byte-identical file alone is not enough evidence to overwrite it.
- Five packages contain reviewed `Replaces` fields for obsolete/conflicting
  package names. The helper verifies those actual archive fields against the
  archive review and refuses if any target has a dpkg record on any
  architecture, including residual config-files. The current read-only device
  check found no such records. `Conflicts` and `Breaks` are also checked against
  installed package records and Debian version relations.
- The read-only planner itself does not inspect paths or solve dependencies.
  Separate target inspection captured all 32 pre-existing non-directory
  archive targets and their `dpkg -S` owners/content/metadata in the JSON
  inventory. The historical isolated solver is tied to this same status hash;
  it is not a new solver run against live repositories.

Decision: the local helper now has a bounded recovery design: preserve the
verified 26 local archives and preinstall numeric-owner metadata, run under the
caller's maintenance lock, and resume only the originally absent/exact-partial
candidates without restoring stale dpkg state or automatically removing libraries. The
host fixtures cover partial resume, multi-owner paths, `Replaces` takeover,
unsupported dependency qualifiers, and symlink ancestors. The helper has not
been run with `--apply` or `--resume` on the device; an interrupted-transaction
recovery test and post-install loader/game checks remain release gates. No
updater entrypoint, dated ZIP, marker, or device package state changed.

Host validation outputs:

- `python3 -m py_compile drafts/portmaster-armhf-closure/*.py`: passed.
- `python3 drafts/portmaster-armhf-closure/host-fixture/test_install_helpers.py`:
  passed; covers exact partial resume admission, comma-separated multiarch
  owners, controlled `/sbin`/`/usr/sbin` `PATH`, required-tool gating,
  rejecting unknown owners and `:any`, rejecting a live `Replaces` target, and
  refusing a noncanonical symlink ancestor.
- Planner run against the captured dpkg status: 26 absent ARMhf additions;
  no package-state conflicts.
- Package-manifest/archive-review crosswalk: all 26 versions, architectures,
  `Multi-Arch`, and dependencies match; actual archive review has five
  `Replaces` clauses, and no such target record was found in the device status.
- A device `--check` passed for 26 candidate packages. The subsequent
  `--apply` attempt was refused by dpkg before unpack because sudo's inherited
  `PATH` omitted `/sbin` and `/usr/sbin`, so `ldconfig` and
  `start-stop-daemon` could not be found. The device dpkg audit remained clean;
  no package-state mutation was reported. The helper now passes a fixed system
  `PATH` to subprocesses and checks all required tools before creating backup
  data. This fix has not been retried on the device.
- Full installer preflight was not run on this host because `dpkg` and
  `dpkg-deb` are unavailable here. No device package transaction completed.
