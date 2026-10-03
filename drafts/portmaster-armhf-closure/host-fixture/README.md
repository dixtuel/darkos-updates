# Read-only planner host fixture

`fixtures.json` contains tiny dpkg-status examples and the expected class for a
three-package slice of the pinned manifest. It covers absent packages, exact
versions already installed, an ARMhf version mismatch, a `Multi-Arch: same`
version mismatch on ARM64, and a half-configured package. The planner never
changes package state. Its output remains a state classification, not an
installation approval.

`test_install_helpers.py` also verifies the helper's fixed system `PATH`
includes `/sbin` and `/usr/sbin`, checks that missing `ldconfig` and
`start-stop-daemon` are caught before a write phase, and exercises package
ownership, partial resume, `Replaces`, dependency qualifier,
ancestor-symlink, and EmulationStation-selected ROM-card checks. The compat
bundle fixture also validates the built 57-member ZIP and refuses checksum,
traversal, duplicate-member, and symlink-member failures.

The captured historical device status has 1,276 package records and classifies
all 26 ARMhf candidates as absent. That restates the old isolated solver input;
it is not a current device observation and does not settle dependencies,
filesystem ownership/collisions, card backup, or rollback. See
`../INSTALL-DESIGN.md`.
