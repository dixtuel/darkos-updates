#!/usr/bin/env python3
"""Exercise the R5 package installer against isolated /roms and /roms2 roots."""
import hashlib
import os
import pathlib
import subprocess
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "10032026-r5/darkosupdate10032026-r5.zip"
INSTALLER = ROOT / "10032026-r5/install-r5.py"
DIGEST = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
LEGACY = (
    ".update12242025", ".update12312025", ".update01082026",
    ".update01162026", ".update01302026",
)
STAGES = (
    ".update10032026", ".update10032026-r1", ".update10032026-compat",
    ".update10032026-r2", ".update10032026-r3", ".update10032026-r4",
)


def setup(root, rom_root):
    config_dir = root / "home/ark/.config"
    config_dir.mkdir(parents=True)
    (config_dir / ".VERSION").write_text("10032026-r4\n")
    for marker in (*LEGACY, *STAGES):
        (config_dir / marker).touch()
    card_config = root / rom_root / "nds/dsperate/dsperate.ini"
    card_config.parent.mkdir(parents=True)
    card_config.write_text(
        "[paths]\nsaves = /roms2/nds/dsperate/saves\n"
        "states = /roms2/nds/dsperate/states\ncheats = /roms2/nds/cheats\n\n"
        "[video]\nlayout = horizontal\nframeskip = 1\n\n"
        "[emu]\nfast_load = false\n\n[padhotkeys]\nmodifier = guide\n"
    )
    global_config = root / "opt/DSperate/config/dsperate.ini"
    global_config.parent.mkdir(parents=True)
    global_config.write_text(
        "[paths]\nsaves = /roms/nds/dsperate/saves\n"
        "states = /roms/nds/dsperate/states\ncheats = /roms/nds/cheats\n\n"
        "[emu]\n\n[padhotkeys]\n"
    )
    return config_dir, card_config, global_config


def run(root, rom_root, digest):
    env = os.environ.copy()
    env["DARKOS_R5_TEST_ROOT"] = str(root)
    return subprocess.run(
        ["python3", str(INSTALLER), rom_root, str(ARCHIVE), digest],
        env=env, capture_output=True, text=True,
    )


for rom_root in ("roms", "roms2"):
    with tempfile.TemporaryDirectory(prefix=f"r5-{rom_root}-") as temp:
        root = pathlib.Path(temp)
        config_dir, card_config, global_config = setup(root, rom_root)
        result = run(root, rom_root, DIGEST)
        if result.returncode:
            raise AssertionError(f"{rom_root}: installer failed: {result.stdout} {result.stderr}")
        data = card_config.read_text()
        expected = {
            "cpu_oc = false", "timing_oc = false", "modifier = guide",
            "quit = start+back", "pause = guide", "save_state = mod+rightshoulder",
            "load_state = mod+leftshoulder", "layout_next = +righttrigger",
            "layout_prev = mod++lefttrigger", "screen_swap = +lefttrigger", "mic = leftstick",
            f"saves = /{rom_root}/nds/dsperate/saves",
            f"states = /{rom_root}/nds/dsperate/states",
            f"cheats = /{rom_root}/nds/cheats", "layout = horizontal", "frameskip = 1",
            "fast_load = false",
        }
        missing = expected - set(data.splitlines())
        if missing:
            raise AssertionError(f"{rom_root}: settings were lost/missing: {sorted(missing)}")
        if (config_dir / ".VERSION").read_text() != "10032026-r5\n" or not (config_dir / ".update10032026-r5").exists():
            raise AssertionError(f"{rom_root}: version/marker did not advance")
        tool = root / "opt/system/Advanced/Restore Default DSperate Settings.sh"
        if not tool.is_file() or not os.access(tool, os.X_OK):
            raise AssertionError(f"{rom_root}: restore tool is missing or not executable")
        subprocess.run(["bash", "-n", str(tool)], check=True)
        backup = root / rom_root / "backup/darkosre-update/10032026-r5"
        before = hashlib.sha256((backup / "rollback.tar").read_bytes()).hexdigest()
        if not (backup / "backup-ready").is_file():
            raise AssertionError(f"{rom_root}: rollback readiness marker missing")
        second = run(root, rom_root, DIGEST)
        if second.returncode:
            raise AssertionError(f"{rom_root}: repeat install failed: {second.stdout} {second.stderr}")
        after = hashlib.sha256((backup / "rollback.tar").read_bytes()).hexdigest()
        if before != after:
            raise AssertionError(f"{rom_root}: retry replaced the original rollback snapshot")
        bad = run(root, rom_root, "0" * 64)
        if bad.returncode == 0:
            raise AssertionError(f"{rom_root}: bad package checksum was accepted")
        print(f"{rom_root}: merge, user-setting preservation, ROM routing, rollback, retry and bad-hash rejection passed")

print("R5 installer fixtures passed for both supported ROM roots; no system or device paths were changed.")
