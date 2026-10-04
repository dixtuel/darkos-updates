#!/usr/bin/env python3
"""Exercise R6 install, ROM-root routing, rollback and retry in temp roots."""
import hashlib
import os
import pathlib
import subprocess
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGE = ROOT / "10032026-r6"
ARCHIVE = STAGE / "darkosupdate10032026-r6.zip"
INSTALLER = STAGE / "install-r6.py"
DIGEST = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
PREVIOUS = (
    ".update10032026", ".update10032026-r1", ".update10032026-compat",
    ".update10032026-r2", ".update10032026-r3", ".update10032026-r4",
    ".update10032026-r5",
)
PAYLOAD_PATHS = (
    "usr/bin/emulationstation/emulationstation",
    "usr/bin/emulationstation/resources/network.svg",
    "usr/bin/emulationstation/resources/fontawesome-webfont.ttf",
    "usr/share/doc/emulationstation/OFL-1.1.txt",
)


def setup(root, selected, configured=None):
    config = root / "home/ark/.config"
    config.mkdir(parents=True)
    (config / ".VERSION").write_text("10032026-r5\n")
    for marker in PREVIOUS:
        (config / marker).touch()
    es = root / "etc/emulationstation/es_systems.cfg"
    es.parent.mkdir(parents=True)
    active = configured or selected
    es.write_text(f"<systemList><system><path>/{active}/ports</path></system></systemList>\n")
    old_binary = root / PAYLOAD_PATHS[0]
    old_binary.parent.mkdir(parents=True)
    old_binary.write_bytes(b"previous-r36-emulationstation\n")
    old_binary.chmod(0o755)
    old_icon = root / PAYLOAD_PATHS[1]
    old_icon.parent.mkdir(parents=True, exist_ok=True)
    old_icon.write_text("old network icon\n")
    return config, es


def run(root, rom_root, expected=DIGEST):
    env = os.environ.copy()
    env["DARKOS_R6_TEST_ROOT"] = str(root)
    return subprocess.run(["python3", str(INSTALLER), rom_root, str(ARCHIVE), expected],
                          env=env, capture_output=True, text=True)


for rom_root in ("roms", "roms2"):
    with tempfile.TemporaryDirectory(prefix=f"r6-{rom_root}-") as temp:
        root = pathlib.Path(temp)
        config, es = setup(root, rom_root)
        before_es = es.read_bytes()
        result = run(root, rom_root)
        if result.returncode:
            raise AssertionError(f"{rom_root}: install failed: {result.stdout} {result.stderr}")
        if es.read_bytes() != before_es:
            raise AssertionError(f"{rom_root}: installer changed ES ROM paths")
        with zipfile.ZipFile(ARCHIVE) as package:
            for path in PAYLOAD_PATHS:
                installed = root / path
                if installed.read_bytes() != package.read(path):
                    raise AssertionError(f"{rom_root}: payload mismatch: {path}")
        binary = root / PAYLOAD_PATHS[0]
        if binary.stat().st_mode & 0o777 != 0o755:
            raise AssertionError(f"{rom_root}: executable mode was not retained")
        if (config / ".VERSION").read_text() != "10032026-r6\n" or not (config / ".update10032026-r6").exists():
            raise AssertionError(f"{rom_root}: R6 version/marker did not advance")
        rollback = root / rom_root / "backup/darkosre-update/10032026-r6"
        tar = rollback / "rollback.tar"
        first_hash = hashlib.sha256(tar.read_bytes()).hexdigest()
        subprocess.run(["sha256sum", "-c", str(rollback / "rollback.sha256")], cwd=rollback,
                       check=True, stdout=subprocess.DEVNULL)
        members = subprocess.check_output(["tar", "-tf", str(tar)], text=True).splitlines()
        if PAYLOAD_PATHS[0] not in members or "home/ark/.config/.VERSION" not in members:
            raise AssertionError(f"{rom_root}: rollback archive misses replaced state")
        retry = run(root, rom_root)
        if retry.returncode:
            raise AssertionError(f"{rom_root}: idempotent retry failed: {retry.stdout} {retry.stderr}")
        if hashlib.sha256(tar.read_bytes()).hexdigest() != first_hash:
            raise AssertionError(f"{rom_root}: retry replaced the first rollback snapshot")
        bad = run(root, rom_root, "0" * 64)
        if bad.returncode == 0:
            raise AssertionError(f"{rom_root}: wrong package hash was accepted")
        mismatch = run(root, "roms2" if rom_root == "roms" else "roms")
        if mismatch.returncode == 0:
            raise AssertionError(f"{rom_root}: mismatch between active card and requested root was accepted")
        print(f"/{rom_root}: install, active-root guard, payloads, rollback, idempotent retry, and bad-hash rejection passed")

print("R6 isolated installer fixtures passed; no device or system paths were changed.")
