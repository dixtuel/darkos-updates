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
print("Updater sequence resolver passed 10 isolated version/marker cases and the legacy-marker assertion; no system paths were changed.")
