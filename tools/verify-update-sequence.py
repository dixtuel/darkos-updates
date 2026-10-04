#!/usr/bin/env python3
"""Exercise the updater's read-only version/marker resolver in plan-only mode."""

import os
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
UPDATER = ROOT / "dArkOSUpdate.sh"
LEGACY = (
    ".update12242025",
    ".update12312025",
    ".update01082026",
    ".update01162026",
    ".update01302026",
)
BASE = ".update10032026"
R1 = ".update10032026-r1"
R2 = ".update10032026-r2"
R3 = ".update10032026-r3"
R4 = ".update10032026-r4"
COMPAT = ".update10032026-compat"


def run_case(version, markers, expected, success=True):
    with tempfile.TemporaryDirectory(prefix="update-sequence-") as temp:
        root = pathlib.Path(temp)
        config = root / "config"
        config.mkdir()
        (config / ".VERSION").write_text(version + "\n")
        for marker in markers:
            (config / marker).touch()
        compatible = root / "compatible"
        compatible.write_bytes(b"anbernic,r36s\x00rockchip,rk3326\x00")
        log = root / "update.log"
        env = os.environ.copy()
        env.update(
            DARKOS_UPDATE_CONFIG_DIR=str(config),
            DARKOS_DEVICE_COMPAT_FILE=str(compatible),
            DARKOS_UPDATE_LOG_FILE=str(log),
            DARKOS_UPDATE_PLAN_ONLY="1",
            TERM="xterm",
        )
        result = subprocess.run(
            ["bash", str(UPDATER)], env=env, capture_output=True, text=True
        )
        if success and result.returncode != 0:
            raise AssertionError(f"{version}: expected success, got {result.returncode}: {result.stderr} {result.stdout}")
        if not success and result.returncode == 0:
            raise AssertionError(f"{version}: expected fail-closed state, got success: {result.stdout}")
        if success and f"next={expected}\n" not in result.stdout:
            raise AssertionError(f"{version}: expected next={expected}, got {result.stdout!r}")
        return result.stdout


all_legacy = set(LEGACY)
run_case("03082026", set(), "", success=False)
run_case("03082026", all_legacy - {LEGACY[2]}, "", success=False)
run_case("03082026", all_legacy, "10032026")
run_case("10032026", all_legacy | {BASE}, "10032026-r1")
run_case("10032026-r1", all_legacy | {BASE, R1}, "10032026-compat")
run_case("10032026-r2", all_legacy | {BASE, R1, R2, COMPAT}, "10032026-r3")
run_case("10032026-r3", all_legacy | {BASE, R1, R2, R3}, "10032026-compat")
run_case("10032026-r4", all_legacy | {BASE, R1, R2, R3, R4, COMPAT}, "none")
run_case("02062026", all_legacy, "", success=False)
run_case("10032026-r2", all_legacy | {BASE, R2}, "", success=False)
text = UPDATER.read_text()
if 'touch "$UPDATE_DONE"' in text or 'touch "/home/ark/.config/.update01302026"' not in text:
    raise AssertionError("legacy update code must use its explicit marker, not an unset sentinel")

# Reboot-required base/R1 installers intentionally stop for a reboot. Once
# those are complete, the no-reboot compatibility/R2/R3/R4 stages must finish
# in one updater invocation, with only a successful R4 install rebooting.
r2_start = text.index('PATCH_VERSION="10032026-r2"')
r3_start = text.index('PATCH_VERSION="10032026-r3"', r2_start)
r4_start = text.index('PATCH_VERSION="10032026-r4"', r3_start)
r4_end = text.index("# All required stages already have completion markers", r4_start)
r2_block = text[r2_start:r3_start]
r3_block = text[r3_start:r4_start]
r4_block = text[r4_start:r4_end]
if "R2 completed successfully; continuing" not in r2_block or "exit 187" in r2_block or "prune_superseded_backups" not in r2_block:
    raise AssertionError("successful R2 must prune older backups and continue to R3 in the same invocation")
if "R3 completed successfully; continuing to R4" not in r3_block or "exit 187" in r3_block or "prune_superseded_backups" not in r3_block:
    raise AssertionError("successful R3 must prune older backups and continue to R4 in the same invocation")
if "All available updates through R4 completed" not in r4_block or "sudo systemctl reboot" not in r4_block or "prune_superseded_backups" not in r4_block:
    raise AssertionError("successful R4 must trigger the final device reboot")
base_start = text.index('if [ ! -f "/home/ark/.config/.update10032026" ]; then')
r1_start = text.index('PATCH_VERSION="10032026-r1"', base_start)
compat_start = text.index('COMPAT_VERSION="10032026-compat"', r1_start)
base_block = text[base_start:r1_start]
r1_block = text[r1_start:compat_start]
for name, block in (("base", base_block), ("R1", r1_block)):
    if "msgbox" not in block or "/roms/tools" not in block or "choose Update from EmulationStation" not in block:
        raise AssertionError(f"{name} mandatory reboot must tell users how to resume updates")
if "No further updater run is needed" not in r4_block:
    raise AssertionError("final reboot message must tell users the update chain is complete")
no_update_start = text.index('if [ -z "$NEXT_STAGE" ]; then')
no_update_end = text.index("fi", no_update_start)
if "reboot" in text[no_update_start:no_update_end].lower():
    raise AssertionError("opening the updater when already current must not trigger a reboot")
print("Updater sequence passed 10 isolated version/marker cases, continuation/final-reboot policy checks, and the legacy-marker assertion; no system paths were changed.")
