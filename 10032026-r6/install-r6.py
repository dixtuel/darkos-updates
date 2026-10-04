#!/usr/bin/env python3
"""Install the R36 EmulationStation status-indicator update with rollback."""
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

PAYLOADS = {
    "usr/bin/emulationstation/emulationstation": ("/usr/bin/emulationstation/emulationstation", "4c862d336e468f0aa2e5178f5d1bd66521fd9f192525097e4158ea63f25a8dad", 0o755),
    "usr/bin/emulationstation/resources/network.svg": ("/usr/bin/emulationstation/resources/network.svg", "a2dd8e8eeb06b560c5b2a2ec97c344b1b23a9cdb79d4e0739a5333bf6bf08d9b", 0o644),
    "usr/bin/emulationstation/resources/fontawesome-webfont.ttf": ("/usr/bin/emulationstation/resources/fontawesome-webfont.ttf", "aa58f33f239a0fb02f5c7a6c45c043d7a9ac9a093335806694ecd6d4edc0d6a8", 0o644),
    "usr/share/doc/emulationstation/OFL-1.1.txt": ("/usr/share/doc/emulationstation/OFL-1.1.txt", "1a7adaa2c86cedfd6c7f5c0c7c72fd6d3e02cd0c9593f21fdb53c89bb2b130ec", 0o644),
}


def fail(message):
    raise SystemExit(f"R6: {message}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_target(root, target):
    relative = target.relative_to(root)
    parent = root
    for part in relative.parts[:-1]:
        parent = parent / part
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            fail(f"unsafe target parent: {parent}")
    if target.is_symlink() or (target.exists() and not target.is_file()):
        fail(f"target is not a regular file: {target}")
    if target.exists() and target.stat().st_nlink != 1:
        fail(f"refusing hard-linked target: {target}")


def xattrs(path):
    try:
        return {key: os.getxattr(path, key, follow_symlinks=False)
                for key in os.listxattr(path, follow_symlinks=False)}
    except (AttributeError, OSError):
        return {}


def atomic_write(path, data, default_mode, owner):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.stat(follow_symlinks=False) if path.exists() else None
    old_attrs = xattrs(path) if old else {}
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.r6.", dir=path.parent)
    temporary = pathlib.Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if old:
            os.chown(temporary, old.st_uid, old.st_gid)
            os.chmod(temporary, stat.S_IMODE(old.st_mode))
            for key, value in old_attrs.items():
                os.setxattr(temporary, key, value, follow_symlinks=False)
        else:
            os.chown(temporary, owner.st_uid, owner.st_gid)
            os.chmod(temporary, default_mode)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def main():
    if len(sys.argv) != 4:
        fail("usage: install-r6.py roms|roms2 package.zip expected-sha256")
    rom_name, archive_name, expected_archive = sys.argv[1:]
    if rom_name not in ("roms", "roms2"):
        fail("unsupported active ROM root")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_archive) or digest(pathlib.Path(archive_name).read_bytes()) != expected_archive:
        fail("package checksum mismatch")
    test_root_value = os.environ.get("DARKOS_R6_TEST_ROOT")
    root = pathlib.Path(test_root_value).resolve() if test_root_value else pathlib.Path("/")
    selected_mount = root / rom_name
    config_dir = root / "home/ark/.config"
    version_path = config_dir / ".VERSION"
    if test_root_value:
        selected_mount.mkdir(parents=True, exist_ok=True)
    else:
        if not selected_mount.is_mount() or selected_mount.is_symlink():
            fail(f"/{rom_name} is not a mounted, safe ROM card")
        if b"rk3326" not in (root / "proc/device-tree/compatible").read_bytes():
            fail("this OTA is restricted to RK3326 firmware")
    config = (root / "etc/emulationstation/es_systems.cfg").read_text(errors="replace")
    configured = set(re.findall(r"<path>(/roms2?)(?:/[^<]*)?</path>", config))
    if configured != {f"/{rom_name}"}:
        fail("active EmulationStation paths changed or mix ROM cards")
    version = version_path.read_text().strip()
    if version not in ("10032026-r5", "10032026-r6"):
        fail(f"expected R5 or an interrupted R6 retry, found {version}")
    previous = (".update10032026", ".update10032026-r1", ".update10032026-compat",
                ".update10032026-r2", ".update10032026-r3", ".update10032026-r4",
                ".update10032026-r5")
    if any(not (config_dir / marker).is_file() for marker in previous):
        fail("one or more required base/R1/R2/R3/R4/R5 completion markers are missing")
    archive = pathlib.Path(archive_name)
    with zipfile.ZipFile(archive) as package:
        expected_names = {"install-r6.py", *PAYLOADS}
        if set(package.namelist()) != expected_names or package.testzip() is not None:
            fail("package contents or CRC validation failed")
        payload = {name: package.read(name) for name in PAYLOADS}
    for member, data in payload.items():
        if digest(data) != PAYLOADS[member][1]:
            fail(f"payload hash mismatch: {member}")
    binary = payload["usr/bin/emulationstation/emulationstation"]
    if len(binary) < 20 or binary[:4] != b"\x7fELF" or binary[4:6] != b"\x02\x01" or int.from_bytes(binary[18:20], "little") != 183:
        fail("EmulationStation payload is not a little-endian AArch64 ELF")

    targets = {member: root / relative.lstrip("/") for member, (relative, _, _) in PAYLOADS.items()}
    marker = config_dir / ".update10032026-r6"
    for target in (*targets.values(), version_path, marker):
        safe_target(root, target)
    backup_dir = selected_mount / "backup/darkosre-update/10032026-r6"
    for directory in (selected_mount / "backup", selected_mount / "backup/darkosre-update", backup_dir):
        safe_target(root, directory / ".sentinel")
        if directory.is_symlink():
            fail(f"unsafe rollback directory: {directory}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_tar, backup_sum, ready = (backup_dir / "rollback.tar", backup_dir / "rollback.sha256", backup_dir / "backup-ready")
    for artifact in (backup_tar, backup_sum, ready):
        if artifact.is_symlink() or (artifact.exists() and not artifact.is_file()):
            fail(f"unsafe rollback artifact: {artifact}")
    if not ready.exists():
        paths = [str(path.relative_to(root)) for path in (*targets.values(), version_path,
                 config_dir / ".update10032026-r5") if path.is_file()]
        subprocess.run(["tar", "--numeric-owner", "--acls", "--xattrs", "-cpf", str(backup_tar), "-C", str(root), *paths], check=True)
        backup_sum.write_text(f"{digest(backup_tar.read_bytes())}  rollback.tar\n")
        subprocess.run(["sha256sum", "-c", str(backup_sum)], cwd=backup_dir, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["tar", "-tf", str(backup_tar)], check=True, stdout=subprocess.DEVNULL)
        ready.write_text("R6 rollback snapshot verified\n")
    else:
        if not backup_tar.is_file() or not backup_sum.is_file():
            fail("R6 rollback marker exists but its snapshot is incomplete")
        subprocess.run(["sha256sum", "-c", str(backup_sum)], cwd=backup_dir, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["tar", "-tf", str(backup_tar)], check=True, stdout=subprocess.DEVNULL)

    for member, data in payload.items():
        target = targets[member]
        relative, _, mode = PAYLOADS[member]
        target.parent.mkdir(parents=True, exist_ok=True)
        owner_source = target if target.exists() else target.parent
        atomic_write(target, data, mode, owner_source.stat())
    config_owner = config_dir.stat()
    atomic_write(marker, b"", 0o644, config_owner)
    atomic_write(version_path, b"10032026-r6\n", 0o644, config_owner)
    print(f"R6 installed with verified rollback on /{rom_name}; user settings and ROM/save paths were not changed.")


if __name__ == "__main__":
    main()
