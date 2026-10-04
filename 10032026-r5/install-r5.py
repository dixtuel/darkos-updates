#!/usr/bin/env python3
"""Install the R36S DSperate defaults/reset-tool OTA without replacing user settings."""
import hashlib
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

PROFILE_KEYS = {
    "emu": {
        "cpu_oc": "false",
        "timing_oc": "false",
        "fast_load": "true",
    },
    "padhotkeys": {
        "modifier": "none",
        "quit": "start+back",
        "pause": "guide",
        "save_state": "mod+rightshoulder",
        "load_state": "mod+leftshoulder",
        "layout_next": "+righttrigger",
        "layout_prev": "mod++lefttrigger",
        "screen_swap": "+lefttrigger",
        "mic": "leftstick",
    },
}
PROFILE_SHA256 = "55b4717352c581a148af0235b2abaa4231b669f95194a0b6f57decf78c09046f"
TOOL_SHA256 = "bc209ab9a27bc40bb3702ef8588e9051c6b2224cda9779851b9b2e4609494297"
PROFILE_MEMBER = "dsperate.ini"
TOOL_MEMBER = "Restore Default DSperate Settings.sh"
TARGETS = {
    PROFILE_MEMBER: pathlib.PurePosixPath("opt/DSperate/config/dsperate.ini"),
    TOOL_MEMBER: pathlib.PurePosixPath("opt/system/Advanced/Restore Default DSperate Settings.sh"),
}


def fail(message):
    raise SystemExit(f"R5: {message}")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def active_sections(text):
    section = None
    active = {}
    for line in text.splitlines():
        match = re.match(r"^\s*\[([^]]+)\]\s*(?:[#;].*)?$", line)
        if match:
            section = match.group(1).strip().lower()
            active.setdefault(section, set())
            continue
        if section is None or re.match(r"^\s*[#;]", line):
            continue
        match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*=", line)
        if match:
            active.setdefault(section, set()).add(match.group(1).lower())
    return active


def merge_profile(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail("DSperate config is not UTF-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    present = active_sections(text)
    additions = {section: {key: value for key, value in values.items()
                           if key not in present.get(section, set())}
                 for section, values in PROFILE_KEYS.items()}
    out = []
    section = None
    inserted = set()
    for line in lines:
        match = re.match(r"^\s*\[([^]]+)\]", line)
        if match:
            if section and section in additions and section not in inserted:
                out.extend(f"{key} = {value}" for key, value in additions[section].items())
                inserted.add(section)
            section = match.group(1).strip().lower()
            out.append(line)
            if section in additions and section not in inserted:
                out.extend(f"{key} = {value}" for key, value in additions[section].items())
                inserted.add(section)
            continue
        out.append(line)
    if section and section in additions and section not in inserted:
        out.extend(f"{key} = {value}" for key, value in additions[section].items())
        inserted.add(section)
    for name, values in additions.items():
        if values and name not in inserted:
            if out and out[-1] != "":
                out.append("")
            out.append(f"[{name}]")
            out.extend(f"{key} = {value}" for key, value in values.items())
    result = newline.join(out) + (newline if text.endswith(("\n", "\r")) else "")
    return result.encode("utf-8")


def route_rom_paths(data, rom_root_name):
    text = data.decode("utf-8")
    paths = {
        "saves": f"/{rom_root_name}/nds/dsperate/saves",
        "states": f"/{rom_root_name}/nds/dsperate/states",
        "cheats": f"/{rom_root_name}/nds/cheats",
    }
    for key, value in paths.items():
        text, count = re.subn(rf"(?m)^\s*{key}\s*=.*$", f"{key} = {value}", text)
        if count != 1:
            fail(f"expected exactly one active {key} path in DSperate config")
    return text.encode("utf-8")


def target_path(root, relative):
    return root.joinpath(*relative.parts)


def ensure_safe_path(root, path):
    rel = path.relative_to(root)
    current = root
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            fail(f"unsafe target directory: {current}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        fail(f"target is not a regular file: {path}")
    if path.exists() and path.stat().st_nlink != 1:
        fail(f"refusing hard-linked target: {path}")


def xattrs(path):
    try:
        return {name: os.getxattr(path, name, follow_symlinks=False)
                for name in os.listxattr(path, follow_symlinks=False)}
    except (AttributeError, OSError):
        return {}


def atomic_write(path, data, default_owner=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    old_stat = path.stat(follow_symlinks=False) if path.exists() else None
    old_xattrs = xattrs(path) if old_stat else {}
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.r5.", dir=path.parent)
    temp = pathlib.Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if old_stat:
            os.chown(temp, old_stat.st_uid, old_stat.st_gid)
            os.chmod(temp, stat.S_IMODE(old_stat.st_mode))
            for name, value in old_xattrs.items():
                os.setxattr(temp, name, value, follow_symlinks=False)
        else:
            os.chmod(temp, 0o755 if path.name.endswith(".sh") else 0o644)
            if default_owner is not None:
                os.chown(temp, default_owner[0], default_owner[1])
        os.replace(temp, path)
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def main():
    if len(sys.argv) != 4:
        fail("usage: install-r5.py roms|roms2 package.zip expected-sha256")
    rom_root_name, archive_name, expected_archive_hash = sys.argv[1:]
    if rom_root_name not in ("roms", "roms2"):
        fail("unsupported active ROM root")
    test_root = os.environ.get("DARKOS_R5_TEST_ROOT")
    root = pathlib.Path(test_root).resolve() if test_root else pathlib.Path("/")
    selected_mount = root / rom_root_name
    if test_root:
        selected_mount.mkdir(parents=True, exist_ok=True)
    else:
        if not selected_mount.is_mount() or selected_mount.is_symlink():
            fail(f"/{rom_root_name} is not a mounted, safe ROM card")
        config_text = (root / "etc/emulationstation/es_systems.cfg").read_text(errors="replace")
        selected = set(re.findall(r"<path>(/roms2?)(?:/[^<]*)?</path>", config_text))
        if selected != {f"/{rom_root_name}"}:
            fail("active EmulationStation paths changed or mix ROM cards")
        compatible = (root / "proc/device-tree/compatible").read_bytes()
        if b"rk3326" not in compatible:
            fail("this OTA is restricted to RK3326 firmware")
    config_dir = root / "home/ark/.config"
    version = (config_dir / ".VERSION").read_text().strip()
    if version not in ("10032026-r4", "10032026-r5"):
        fail(f"expected R4 or an interrupted R5 retry, found {version}")
    for marker in (".update10032026", ".update10032026-r1", ".update10032026-compat",
                   ".update10032026-r2", ".update10032026-r3", ".update10032026-r4"):
        if not (config_dir / marker).is_file():
            fail(f"required update marker {marker} is missing")
    archive = pathlib.Path(archive_name)
    if sha256(archive.read_bytes()) != expected_archive_hash:
        fail("package checksum mismatch")
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        if sorted(names) != sorted(("install-r5.py", PROFILE_MEMBER, TOOL_MEMBER)):
            fail("package contains unexpected or missing files")
        if package.testzip() is not None:
            fail("package CRC check failed")
        payload = {name: package.read(name) for name in (PROFILE_MEMBER, TOOL_MEMBER)}
    if sha256(payload[PROFILE_MEMBER]) != PROFILE_SHA256 or sha256(payload[TOOL_MEMBER]) != TOOL_SHA256:
        fail("payload hash mismatch")
    targets = {name: target_path(root, relative) for name, relative in TARGETS.items()}
    rom_config = root / rom_root_name / "nds/dsperate/dsperate.ini"
    targets["active-config"] = rom_config
    for path in targets.values():
        ensure_safe_path(root, path)
    # Existing stage backup is immutable once complete; a retry must verify it.
    backup_dir = selected_mount / "backup/darkosre-update/10032026-r5"
    for path in (selected_mount / "backup", selected_mount / "backup/darkosre-update", backup_dir):
        ensure_safe_path(root, path / ".sentinel")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for part in (selected_mount / "backup", selected_mount / "backup/darkosre-update", backup_dir):
        if part.is_symlink():
            fail(f"unsafe backup directory: {part}")
    backup_tar = backup_dir / "rollback.tar"
    backup_sum = backup_dir / "rollback.sha256"
    ready = backup_dir / "backup-ready"
    for artifact in (backup_tar, backup_sum, ready):
        if artifact.is_symlink() or (artifact.exists() and not artifact.is_file()):
            fail(f"unsafe rollback artifact: {artifact}")
    if not ready.exists():
        to_backup = [*targets.values(), config_dir / ".VERSION", config_dir / ".update10032026-r4"]
        existing = [str(path.relative_to(root)) for path in to_backup if path.is_file()]
        subprocess.run(["tar", "--numeric-owner", "--acls", "--xattrs", "-cpf", str(backup_tar),
                        "-C", str(root), *existing], check=True)
        digest = sha256(backup_tar.read_bytes())
        backup_sum.write_text(f"{digest}  rollback.tar\n")
        subprocess.run(["sha256sum", "-c", str(backup_sum)], cwd=backup_dir, check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["tar", "-tf", str(backup_tar)], check=True, stdout=subprocess.DEVNULL)
        ready.write_text("R5 rollback snapshot verified\n")
    else:
        if not backup_tar.is_file() or not backup_sum.is_file():
            fail("R5 rollback marker exists but snapshot is incomplete")
        subprocess.run(["sha256sum", "-c", str(backup_sum)], cwd=backup_dir, check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["tar", "-tf", str(backup_tar)], check=True, stdout=subprocess.DEVNULL)
    template_path = targets[PROFILE_MEMBER]
    if template_path.exists():
        merged_template = merge_profile(template_path.read_bytes())
    else:
        merged_template = merge_profile(payload[PROFILE_MEMBER])
    config_path = rom_config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        merged_card = merge_profile(config_path.read_bytes())
    else:
        merged_card = merge_profile(merged_template)
    merged_card = route_rom_paths(merged_card, rom_root_name)
    # Apply payload and merged configs only after the backup has been verified.
    atomic_write(template_path, merged_template)
    atomic_write(targets[TOOL_MEMBER], payload[TOOL_MEMBER])
    atomic_write(config_path, merged_card)
    atomic_write(config_dir / ".VERSION", b"10032026-r5\n")
    config_owner = config_dir.stat()
    atomic_write(config_dir / ".update10032026-r5", b"", (config_owner.st_uid, config_owner.st_gid))
    print(f"R5 installed; existing settings were preserved and missing R36 profile keys added on /{rom_root_name}.")


if __name__ == "__main__":
    main()
