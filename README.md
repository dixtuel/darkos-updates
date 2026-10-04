# dArkOSRE-R36 update feed

This repository hosts the updater script and dated OTA packages used by the
maintained [dArkOSRE-R36 firmware](https://github.com/dixtuel/dArkOSRE-R36).
It is an update feed, not a firmware image.

## Supported firmware

The feed targets dArkOSRE-R36 devices using the **RK3326** platform. The
supported starting image is dArkOSRE-R36 **03082026** with its required earlier
update markers present. Devices already at one of the maintained `10032026`
stages may continue only when their version and completion markers agree. If
the expected base markers are missing or inconsistent, the updater stops
without replaying old upstream packages.

This feed is not for vanilla dArkOS, RK3566 devices, or installing a firmware
image. It does not perform a Debian release upgrade or repartition an SD card.

## Update order

The updater reads the installed version and markers, then installs the first
missing stage in order. The compatibility package is a separate step; it does
not change `.VERSION`.

| Stage | Purpose | Details |
| --- | --- | --- |
| `10032026` | Initial maintained R36 OTA from base `03082026` | [Package notes](10032026/README.md) |
| `10032026-r1` | R36 launcher, suspend, backup/restore, and related fixes | [Package notes](10032026-r1/README.md) |
| `10032026-compat` | Pinned PortMaster ARMhf compatibility dependencies | [Package notes](10032026-compat/README.md) |
| `10032026-r2` | Adds DSperate as an optional DS emulator, plus scoped runtime compatibility changes | [Package notes](10032026-r2/README.md) |
| `10032026-r3` | R36 runtime and control follow-up | [Package notes](10032026-r3/README.md) |
| `10032026-r4` | Advanced SD2 launcher repair | [Package notes](10032026-r4/README.md) |
| `10032026-r5` | Complete the DSperate RK3326 defaults and add a controller-operated reset tool | [Package notes](10032026-r5/README.md) |
| `10032026-r6` | Add the R36 EmulationStation Wi-Fi indicator toggle and required resources | [Package notes](10032026-r6/README.md) |

The current feed release is [`ota-10032026-r6`](https://github.com/dixtuel/darkos-updates/releases/tag/ota-10032026-r6).
The migration is split across two required reboot boundaries: starting from
`.VERSION=03082026`, the `10032026` base OTA installs and reboots; after startup,
run the migration helper again or choose **Update** from EmulationStation to
install `10032026-r1`, which also reboots. After that startup, run the helper or
**Update** once more. The compatibility package and R2 through R6 then install
sequentially in that invocation, and a successful R6 install requests the
final reboot. If no stage is pending, the updater reports that the device is
current and does not reboot. No keyboard confirmation is required.

## How the device gets updates

The firmware's `/opt/system/Update.sh` downloads the updater from this
repository's raw `main` branch:

```text
https://raw.githubusercontent.com/dixtuel/darkos-updates/main/dArkOSUpdate.sh
```

The updater downloads each package from its dated directory on the same raw
`main` branch. GitHub Releases provide the matching ZIP and checksum for people
reviewing or downloading a package; they are not the device's feed endpoint.

Devices whose installed update entrypoint still points to the upstream feed
must first use the migration helper attached to the
[firmware repository's migration release](https://github.com/dixtuel/dArkOSRE-R36/releases/tag/r36-updater-migration-20261004).
Follow that helper's instructions and compatibility limits; it changes the
reviewed updater URL and does not flash an image.

## `/roms` and `/roms2`

Before installing a maintained OTA, the updater reads EmulationStation's game
paths and requires exactly one selected ROM root: `/roms` or `/roms2`. It also
checks that the selected path is mounted. If the paths are mixed, unsupported,
or the selected card is not mounted, it stops before applying a package.

Rollback files are stored under `backup/darkosre-update/<stage>/` on the
selected ROM card. Package-specific notes describe any scoped changes to
launchers or SD-switch support. The OTAs do not contain users' ROM collections;
check each package's notes for its exact targets and recovery procedure.

After successful R2 through R6 stages, the updater prunes older completed OTA
snapshots on the selected card only when the newest stage has its completion
marker and its rollback archive passes integrity checks. It keeps the newest
verified rollback. Markerless or incomplete-stage backups, PortMaster
dpkg-recovery data, unrelated backups, and files on the inactive ROM card are
left alone. If the newest snapshot is missing or invalid, cleanup is skipped.

## Contributing and release format

- Keep each OTA in a dated directory with the archive, `README.md`, and
  `SHA256SUMS`. Keep the archive name consistent with the directory and updater.
- Use ZIP paths relative to the device filesystem root; do not include absolute
  paths or traversal entries (`..`).
- Document the target, required base/version, exact file changes, rollback, and
  validation limits in the package notes.
- Validate shell syntax, archive structure, and checksums before proposing a
  change. The repository workflow checks these properties; it does not replace
  physical-device validation.
- To publish a feed release, push an `ota-<MMDDYYYY>`,
  `ota-<MMDDYYYY>-rN`, or `ota-<MMDDYYYY>-compat` tag on a commit already on
  `main`. The workflow validates the dated package and publishes its ZIP and
  checksum. The dated directory on raw `main` remains the device download
  source.
- Keep firmware images and their release process in the firmware repository.

## Repositories

- Maintained firmware: <https://github.com/dixtuel/dArkOSRE-R36>
- Maintained update feed: <https://github.com/dixtuel/darkos-updates>
- Original R36 update source: <https://github.com/southoz/darkos-updates>

The `origin` remote should point to the maintained update fork. The
`r36-upstream` remote is comparison-only; upstream history is reviewed before
changes are adapted into this feed.
