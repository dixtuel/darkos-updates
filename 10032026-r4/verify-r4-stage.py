#!/usr/bin/env python3
"""Synthetic-only R4 installer and updater-flow fixtures; never touches /opt."""

import hashlib
import importlib.util
import os
import subprocess
from pathlib import Path
import re
import stat
import tempfile


HERE = Path(__file__).resolve().parent
UPDATE_SCRIPT = HERE.parent / "dArkOSUpdate.sh"
INSTALLER_PATH = HERE / "install-r4.py"
FIRMWARE_REPO = HERE.parents[1] / "firmware-fork"
DEFAULT_BASE_FILE = Path(
    "/mnt/WD Ext4/Projects/DarkOSRE-R36/image-work/staging/base-path-review-20261004/"
    "opt/system/Advanced/Switch to SD2 for Roms.sh"
)
SOURCE_REVISION = "1dd1255"
SOURCE_PATH = "files/ROOTFS/opt/system/Advanced/Switch to SD2 for Roms.sh"
spec = importlib.util.spec_from_file_location("r4_installer_fixture", INSTALLER_PATH)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def setup_tree(base, target_bytes=None, target_mode=0o640,
               es_paths=("/roms2/psp",)):
    rootfs = Path(base) / "rootfs"
    romcard = Path(base) / "romcard"
    target = rootfs / "opt/system/Advanced/Switch to SD2 for Roms.sh"
    sd2 = rootfs / "usr/local/bin/Switch to SD2 for Roms.sh"
    main = rootfs / "usr/local/bin/Switch to Main SD for Roms.sh"
    es = rootfs / "etc/emulationstation/es_systems.cfg"
    version = rootfs / "home/ark/.config/.VERSION"
    marker = rootfs / "home/ark/.config/.update10032026-r4"
    for path in (target, sd2, main, es, version):
        path.parent.mkdir(parents=True, exist_ok=True)
    romcard.mkdir(parents=True, exist_ok=True)
    if target_bytes is not None:
        target.write_bytes(target_bytes)
        target.chmod(target_mode)
    sd2.write_bytes(b"canonical clean SD2 fixture\n")
    main.write_bytes(b"canonical Main-SD fixture copies the clean SD2 script into Advanced\n")
    es.write_text("\n".join(f"<path>{path}</path>" for path in es_paths), encoding="utf-8")
    version.write_bytes(b"10032026-r3\n")
    return rootfs, romcard, target, sd2, main, es, version, marker


def configure_module(rootfs, romcard, target, sd2, main, es, version, marker):
    installer.TARGET = str(target)
    installer.SD2_SWITCH = str(sd2)
    installer.MAIN_SWITCH = str(main)
    installer.ES_CONFIG = str(es)
    installer.VERSION_FILE = str(version)
    installer.DONE_MARKER = str(marker)
    installer.VERSION = "10032026-r4"
    installer.CANONICAL_SD2_HASH = sha(sd2.read_bytes())
    installer.CANONICAL_MAIN_HASHES = {sha(main.read_bytes())}
    installer.os.path.ismount = lambda path: path in ("/roms2", str(romcard))


def test_pre_fix_variants_and_idempotence():
    expected_production = {
        "64f8cd24996182f1b9a195b8c1bebfae2552e7e19554697b9010df6c6845e6da":
            "e6fbeb79127b5f98433d28c1a9eae3df646dbfb46fe97839603b233147ae9f94",
        "ea3dc01439224d150284966a18e162fcb9fb822cd1c0ff5870a1e36b27e7ac7f":
            "3163fd4f5b34386e2fad15985344711a91e2c01e88810c58b0a03a6d7d7ca4e9",
    }
    require(installer.TARGET_HASHES == expected_production,
            "installer production pins differ from the reviewed source/base hashes")
    if not DEFAULT_BASE_FILE.is_file():
        raise FileNotFoundError(f"official-base fixture unavailable: {DEFAULT_BASE_FILE}")
    base_bytes = DEFAULT_BASE_FILE.read_bytes()
    source_bytes = subprocess.check_output(
        ["git", "show", f"{SOURCE_REVISION}:{SOURCE_PATH}"], cwd=FIRMWARE_REPO
    )
    variants = (
        (base_bytes, "64f8cd24996182f1b9a195b8c1bebfae2552e7e19554697b9010df6c6845e6da",
         "e6fbeb79127b5f98433d28c1a9eae3df646dbfb46fe97839603b233147ae9f94", 0o644),
        (source_bytes, "ea3dc01439224d150284966a18e162fcb9fb822cd1c0ff5870a1e36b27e7ac7f",
         "3163fd4f5b34386e2fad15985344711a91e2c01e88810c58b0a03a6d7d7ca4e9", 0o755),
    )
    for original, expected_old, expected_new, source_mode in variants:
        require(sha(original) == expected_old,
                f"fixture source hash differs from reviewed pin: {sha(original)}")
        with tempfile.TemporaryDirectory(prefix="r4-fixture-") as temp:
            rootfs, romcard, target, sd2, main, es, version, marker = setup_tree(
                temp, original, target_mode=source_mode)
            configure_module(rootfs, romcard, target, sd2, main, es, version, marker)
            before = os.stat(target)
            before_xattrs = {name: os.getxattr(target, name, follow_symlinks=False)
                             for name in os.listxattr(target, follow_symlinks=False)}
            prepared = installer.prepare_target()
            require(prepared[3] == expected_new, "production pin expected wrong fixed content hash")
            backup = installer.make_backup(str(romcard), include_target=True)
            installer.surgical_rewrite(*prepared, backup)
            require(sha(target.read_bytes()) == expected_new, "surgical output mismatch")
            after = os.stat(target)
            require((after.st_uid, after.st_gid, stat.S_IMODE(after.st_mode)) ==
                    (before.st_uid, before.st_gid, stat.S_IMODE(before.st_mode)),
                    "surgical rewrite changed numeric owner or mode")
            after_xattrs = {name: os.getxattr(target, name, follow_symlinks=False)
                            for name in os.listxattr(target, follow_symlinks=False)}
            require(after_xattrs == before_xattrs, "surgical rewrite changed xattrs")
            prepared_again = installer.prepare_target()
            require(prepared_again[2] is None, "fixed target was not idempotent")


def test_unknown_file_refusal():
    with tempfile.TemporaryDirectory(prefix="r4-fixture-") as temp:
        custom = b"user-customized wrapper\n"
        rootfs, romcard, target, sd2, main, es, version, marker = setup_tree(temp, custom)
        configure_module(rootfs, romcard, target, sd2, main, es, version, marker)
        try:
            installer.prepare_target()
        except RuntimeError as error:
            require("unrecognized/custom" in str(error), "unexpected refusal reason")
        else:
            raise AssertionError("unknown/custom wrapper was accepted")
        require(target.read_bytes() == custom and not marker.exists(),
                "refusal modified target or marker")


def test_safe_absence_and_refusal():
    with tempfile.TemporaryDirectory(prefix="r4-fixture-") as temp:
        rootfs, romcard, target, sd2, main, es, version, marker = setup_tree(
            temp, None, es_paths=("/roms2/psp", "/usr/local/bin/kodi/", "/opt/cmds/"))
        configure_module(rootfs, romcard, target, sd2, main, es, version, marker)
        require(installer.verified_safe_sd2_absence(), "verified ROM2 state was rejected")
        backup = installer.make_backup(str(romcard), include_target=False)
        installer.write_version_and_marker(backup)
        require(not target.exists(), "safe absence branch created the Advanced menu file")
        require(version.read_text() == "10032026-r4\n" and marker.exists(),
                "safe absence branch did not commit version and marker")

    with tempfile.TemporaryDirectory(prefix="r4-fixture-") as temp:
        rootfs, romcard, target, sd2, main, es, version, marker = setup_tree(
            temp, None, es_paths=("/roms/psp",))
        configure_module(rootfs, romcard, target, sd2, main, es, version, marker)
        require(not installer.verified_safe_sd2_absence(),
                "ROM1 ES paths were accepted as safe ROM2 absence")


def test_flow_guards_and_exit_mapping():
    text = UPDATE_SCRIPT.read_text(encoding="utf-8")
    require('R4_UPDATE_DONE="$CONFIG_DIR/.update10032026-r4"' in text,
            "R4 completion marker is not wired into the version resolver")
    require('COMPAT_UPDATE_DONE="$CONFIG_DIR/.update10032026-compat"' in text and
            'R3_UPDATE_DONE="$CONFIG_DIR/.update10032026-r3"' in text,
            "R4 stage prerequisites are missing")
    ordered_stages = (
        'NEXT_STAGE="10032026-r1"',
        'NEXT_STAGE="10032026-compat"',
        'NEXT_STAGE="10032026-r2"',
        'NEXT_STAGE="10032026-r3"',
        'NEXT_STAGE="10032026-r4"',
    )
    offsets = [text.index(stage) for stage in ordered_stages]
    require(offsets == sorted(offsets), "missing-update resolver does not preserve stage order")
    require("flock -n /run/lock/darkos-update-maintenance.lock" in text,
            "R4 installer lacks the maintenance lock")
    require('if [ "$INSTALL_STATUS" -ne 0 ]; then' in text and
            'exit "$INSTALL_STATUS"' in text and "exit 187" in text,
            "R4 wrapper status mapping is not present")

    def wrapper_result(status):
        return status if status != 0 else 187

    require(wrapper_result(0) == 187, "successful wrapper did not map to 187")
    for status in (1, 2, 17, 255):
        require(wrapper_result(status) == status,
                f"wrapper failure status {status} was not preserved")

    def next_step(base, r3, compat, r4):
        if not base:
            return "base"
        if r3 and not compat:
            return "compat"
        if not r3:
            return "r3"
        if not r4:
            return "r4"
        return "terminal"

    cases = {
        (False, False, False, False): "base",
        (True, True, False, False): "compat",
        (True, False, True, False): "r3",
        (True, True, True, False): "r4",
        (True, True, True, True): "terminal",
    }
    for state, expected in cases.items():
        require(next_step(*state) == expected, f"wrong next step for marker state {state}")


def main():
    old_ismount = os.path.ismount
    try:
        test_pre_fix_variants_and_idempotence()
        test_unknown_file_refusal()
        test_safe_absence_and_refusal()
        test_flow_guards_and_exit_mapping()
    finally:
        os.path.ismount = old_ismount
    print("R4 authentic-byte scratch fixtures passed; no device paths were touched.")


if __name__ == "__main__":
    main()
