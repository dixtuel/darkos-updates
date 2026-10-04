# dArkOSRE-R36 RK3326 OTA follow-up — 10032026-r2

Target: dArkOSRE-R36 on RK3326, after OTA `10032026` or `10032026-r1`.

## Changes

- Adds upstream DSperate v3.0.0 as an optional third emulator in the existing
  Nintendo DS system. Drastic and Advanced Drastic remain available. The
  launcher uses the game path to select `/roms` or `/roms2`; config, battery
  saves, and save states stay on that same card. The bundled config uses
  DSperate's built-in FreeBIOS and includes the R36S GO-Super controller map.
- Copies `.zip` DS games directly to DSperate. `.7z` games are expanded to a
  temporary hidden directory on the selected ROM card and cleaned up when the
  emulator exits, so large archives do not expand into RAM.
- Installs 21 pinned Debian legacy FFmpeg shared objects for AArch64 and 22
  for ARMhf, with the `libsrt-gnutls.so.1.4` aliases for both and the missing
  `libwebpmux.so.3` alias for ARMhf. The ARMhf `libavcodec.so.58` directly
  needs this WebP mux SONAME. The device's working newer AArch64
  `libwebpmux.so.3` remains untouched. The pinned `libwebpmux3` package and
  its `libwebp6` dependency/version are documented with package hashes and
  notices in the firmware source repository.
- Applies vanilla dArkOS commit `4837de95426d2390f0ac2b8c87e8d29973ce04e` to
  the R36S Mali alias case: removes only `libOpenCL.so -> libMali.so` in both
  ABI directories and leaves Debian's versioned `libOpenCL.so.1` loader intact.
  The RK3566-only Vulkan changes are not copied.
- Keeps a source-repository mirror of the RK3326 PPSSPP, ScummVM, Hypseus,
  retrorun, XRoar, LowResNX, and `parallel_n64` artifacts already delivered by
  OTA `10032026`; this follow-up does not replace those active emulator/core
  binaries again.

## ROM-card and rollback safety

The installer reads the mounted ROM card and checks that the current NDS system
uses that card. It inserts only the `dsperate` emulator choice into the NDS
XML block and corrects the four BaRT backup/restore labels and handler names
in the existing wrapper; it does not copy an EmulationStation XML file or
touch either ROM switch script. It compares all XML `<path>` values and both
switch-script hashes before and after installation. A checksum-verified rollback tar
preserves owners, modes, and symlinks under:

- `/roms2/backup/darkosre-update/10032026-r2` on a two-card device
- `/roms/backup/darkosre-update/10032026-r2` on a one-card device

The installer checks DSperate, each packaged compatibility object with the
matching ABI loader, and the full EmulationStation loader tree before it
records the marker. Empty/wrong-architecture ELF payloads are
rejected before installation. The current DSperate card selector also
survives both directions of the existing SD switch scripts' text rewrites.

## Provenance and license

DSperate source tag: [`beebono/DSperate v3.0.0`](https://github.com/beebono/DSperate/tree/v3.0.0),
commit `1b76c355109c9f7576363ccc023927b3137d3c6f`. The binary is the upstream
`dsperate-v3.0.0-linux-aarch64-static.tar.gz` asset, SHA-256
`83d50fa776097647eabaa93627dae89098f91fc6644e809054556c4caa62db54`. Its
GPL-3.0-or-later source snapshot and license are staged in the maintained
firmware source overlay; confirm publication of matching source before any
binary release.
The compatibility packages, per-package checksums, and Debian copyright
notices are in that repository's
`resources/third-party/portmaster-legacy-compat/` directory.

## Verification limits

Verified earlier: package checksum/ZIP structure and the AArch64 compatibility
objects on the target device; DSperate reports v3.0.0 and resolves SDL2; the
NDS system's actual controller GUID is `GO-Super Gamepad`; the current device
has the Mali OpenCL aliases named by the vanilla fix. A later ARMhf loader
check found the missing WebP mux SONAME. The rebuilt candidate ZIP now
contains the pinned ARMhf library and passed archive/ELF/source-hash checks;
live loader verification of this rebuilt candidate is still pending. These
checks do not prove DS game
compatibility, control/hotkey behavior, saved-state behavior, PortMaster game
audio/video, or improved DS performance. No emulator performance advantage is
claimed. Device gameplay and the visible video-preview/screensaver behavior
must still be checked after installation.

ZIP SHA-256 is listed in [`SHA256SUMS`](SHA256SUMS). The update has no keyboard
confirmation step. In the feed sequence, successful R2 installation continues
to R3 without rebooting; successful R4 installation requests the final reboot.

## Packaging correction before publication

The first local package draft mistakenly included an unrelated, zero-byte
`libwebpmux.so.3` file. On the test device this shadowed the valid system
symlink and prevented EmulationStation from loading (`file too short`). The
device's rollback archive restored the original valid symlink and EmulationStation
started again. The zero-byte file has been removed from the source overlay and
OTA archive. Separately, ELF inspection later established that ARMhf
`libavcodec.so.58` needs a real `libwebpmux.so.3`; the ARMhf-only Debian
compatibility object now exists in the source overlay and in the rebuilt
candidate below. AArch64's valid newer `libwebpmux.so.3.1.1` remains untouched.
The rebuilt candidate still requires physical-device validation before release.

## Integrated hardening snapshot

### Clean-base ARMhf limitation

The official R36 image's QEMU loader results reveal five further ARMhf
dependencies absent from the clean base package inventory: `libzvbi.so.0`,
`libgme.so.0`, `libva-drm.so.2`, `libgcrypt.so.20`, and `libsoxr.so.0`. On the
clean base, the ARMhf FFmpeg loader tree therefore still fails when it reaches
these dependencies, even though the added WebP mux object resolves its own
missing SONAME. The previously updated physical device has a different package history;
complete presence of these ARMhf libraries there still requires verification,
and its state does not represent a clean installation. No guessed packages
were added; package mapping is tracked separately. The installer loader gate
must pass against the target's actual matching-ABI libraries before it
commits the update. Clean-base closure and fresh device verification remain
pending; the local ZIP is not publication-ready.

Current local ZIP SHA-256:
`f64e26fe553a1bae6e9af4379b47e37ee0028e769685d952f049d21097bc69e2`.
The ZIP embeds the hardened installer and the SD-switch-safe DSperate
launcher. It has 55 entries, including only the ARMhf `libwebpmux.so.3.0.1`
object and its relative `.3` link as additions. Existing entry content and
modes are preserved; the two added payloads were compared byte-for-byte with
the source overlay, including the symlink target. The repository validator
passed checksum, structure and ELF checks.

The test device received the scoped BaRT and DSperate-selector fixes with
separate ROM2 rollback archives. Its menu remains active. A prior ARMhf
loader check failed on the missing mux SONAME; this rebuilt ZIP has not yet
been applied or verified by the device loader. A clean installation and final
R4 reboot, plus actual game/controller/audio/save tests, remain pending. This
archive has not been published. A completion marker from an older draft does
establish validation of this rebuilt archive.

## Existing-library collision guard (2026-10-03)

The installer now preserves byte-identical installed libraries and matching links. It aborts before installation when a differing existing library/link would be overwritten. Only the documented zero-byte AArch64 libavcodec.so.58 placeholder is eligible for repair. Six isolated filesystem cases passed; this does not establish package ownership/dependency closure or clean-base/device gameplay validation. The candidate remains unpublished.

## Superseding physical closure evidence — 2026-10-03

The guarded exact26-package ARMhf transaction completed on the physical R36S without upgrades/removals or changes to any pre-existing dpkg record. The reviewed two-path WebP mux correction was applied only to absent paths in the older live R2; it did not replay the older marker. All54 payload objects of this exact55-entry R2 archive subsequently matched device readback byte-for-byte/type-for-type, and all10 main FFmpeg system-path loader checks passed across ARMhf/AArch64 without staging libraries. Production ES remained active and versionR3 unchanged. This supersedes the missing-mux/native-loader pending statements for this specific physical device.

The public feed must install the dedicated compatibility closure before R2 so a clean base gets those26 packages too. No broad Debian upgrade is part of this work. Actual DSperate gameplay, controller/BIOS/save tests and clean-image physical boot remain pending; native loader and byte equality do not establish those outcomes.
