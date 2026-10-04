#!/usr/bin/env python3
"""Apply the one-line R36S Advanced SD2 launcher repair, fail closed."""

import hashlib
import os
import re
import stat
import subprocess
import sys
import tempfile


VERSION = "10032026-r4"
TARGET = "/opt/system/Advanced/Switch to SD2 for Roms.sh"
SD2_SWITCH = "/usr/local/bin/Switch to SD2 for Roms.sh"
MAIN_SWITCH = "/usr/local/bin/Switch to Main SD for Roms.sh"
ES_CONFIG = "/etc/emulationstation/es_systems.cfg"
VERSION_FILE = "/home/ark/.config/.VERSION"
DONE_MARKER = "/home/ark/.config/.update10032026-r4"
ANCHOR = b"  sudo sed -i '/roms\\//s//roms2\\//g' /usr/local/bin/singe.sh\n"
TARGET_HASHES = {
    # Exact original variants; only the unique stale Singe rewrite may differ.
    "64f8cd24996182f1b9a195b8c1bebfae2552e7e19554697b9010df6c6845e6da":
        "e6fbeb79127b5f98433d28c1a9eae3df646dbfb46fe97839603b233147ae9f94",
    "ea3dc01439224d150284966a18e162fcb9fb822cd1c0ff5870a1e36b27e7ac7f":
        "3163fd4f5b34386e2fad15985344711a91e2c01e88810c58b0a03a6d7d7ca4e9",
}
ALREADY_FIXED = set(TARGET_HASHES.values())
CANONICAL_SD2_HASH = "3163fd4f5b34386e2fad15985344711a91e2c01e88810c58b0a03a6d7d7ca4e9"
CANONICAL_MAIN_HASHES = {
    # Readback of this R36S (10/03) and maintained R36 source.
    "3d4b06b172b36e09d13a44eead165d6752ebf3d3b9ea0bfd2a078bb9a99f59fd",
    "5a0b888bf7263c14a6e525cdcb0005b8f10fbebdcd7f25e0799a1c2e93096684",
}


def fail(message):
    raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            fail(f"refusing non-regular file: {path}")
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return digest(b"".join(chunks))
    finally:
        os.close(fd)


def require_regular_nonsymlink(path):
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode):
        fail(f"refusing non-regular or symlink path: {path}")
    require_real_parent_directories(path)
    return info


def require_real_parent_directories(path):
    parent = os.path.dirname(path)
    while parent != "/":
        info = os.lstat(parent)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            fail(f"refusing symlinked parent directory: {parent}")
        parent = os.path.dirname(parent)


def read_es_paths():
    with open(ES_CONFIG, "r", encoding="utf-8") as stream:
        content = stream.read()
    return re.findall(r"<path>([^<]+)</path>", content)


def read_rom_paths():
    # ES also has application entries such as /usr/local/bin/kodi and /opt/cmds;
    # select only actual ROM roots when checking the two-card layout.
    return [path for path in read_es_paths()
            if path.startswith("/roms/") or path.startswith("/roms2/")]


def verify_active_rom_root(rom_root):
    if rom_root not in ("roms", "roms2"):
        fail("invalid ROM-root argument")
    root_path = "/" + rom_root
    if not os.path.ismount(root_path):
        fail(f"/{rom_root} is not an active mountpoint")
    paths = read_rom_paths()
    prefix = f"/{rom_root}/"
    if not paths or any(not path.startswith(prefix) for path in paths):
        fail("EmulationStation paths do not uniquely select the mounted ROM card")
    return root_path


def verified_safe_sd2_absence():
    """Accept absence only when the live SD2 flow can regenerate this file."""
    try:
        require_real_parent_directories(TARGET)
    except (FileNotFoundError, RuntimeError):
        return False
    if not os.path.ismount("/roms2"):
        return False
    paths = read_rom_paths()
    if not paths or any(not path.startswith("/roms2/") for path in paths):
        return False
    try:
        require_regular_nonsymlink(SD2_SWITCH)
        require_regular_nonsymlink(MAIN_SWITCH)
    except (FileNotFoundError, RuntimeError):
        return False
    if file_hash(SD2_SWITCH) != CANONICAL_SD2_HASH:
        return False
    if file_hash(MAIN_SWITCH) not in CANONICAL_MAIN_HASHES:
        return False
    # The exact pinned Main-SD switcher copies the canonical /usr/local SD2
    # switcher into Advanced before removing its Main-SD menu entry.
    return True


def make_backup(root_path, include_target):
    backup_base = os.path.join(root_path, "backup", "darkosre-update", VERSION)
    cursor = root_path
    for component in ("backup", "darkosre-update", VERSION):
        cursor = os.path.join(cursor, component)
        try:
            info = os.lstat(cursor)
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                fail(f"unsafe rollback directory: {cursor}")
        except FileNotFoundError:
            os.mkdir(cursor, 0o755)
    archive = os.path.join(backup_base, "advanced-sd2-wrapper.before.tar")
    checksum_path = archive + ".sha256"
    version_member = VERSION_FILE.lstrip("/")
    members = [version_member]
    require_regular_nonsymlink(VERSION_FILE)
    if include_target:
        require_regular_nonsymlink(TARGET)
        members.append(TARGET.lstrip("/"))
    if os.path.lexists(archive):
        archive_info = os.lstat(archive)
        if not stat.S_ISREG(archive_info.st_mode):
            fail(f"rollback archive is not a regular file: {archive}")
        if not os.path.isfile(checksum_path) or os.path.islink(checksum_path):
            fail(f"rollback archive checksum is missing or unsafe: {checksum_path}")
        with open(archive, "rb") as stream:
            archive_sha = digest(stream.read())
        with open(checksum_path, "r", encoding="ascii") as stream:
            expected_line = stream.read().strip()
        if expected_line != f"{archive_sha}  {os.path.basename(archive)}":
            fail(f"existing rollback archive checksum does not match: {archive}")
        listing = subprocess.run(["tar", "-tf", archive], check=True,
                                 stdout=subprocess.PIPE, text=True).stdout.splitlines()
        if version_member not in listing:
            fail("existing rollback archive does not contain the previous .VERSION")
        if include_target and TARGET.lstrip("/") not in listing:
            fail("existing rollback archive does not contain the Advanced SD2 wrapper")
        return archive
    command = [
        "tar", "--numeric-owner", "--acls", "--xattrs", "--xattrs-include=*",
        "-cpf", archive, "-C", "/", *members,
    ]
    subprocess.run(command, check=True)
    subprocess.run(["tar", "-tf", archive], check=True, stdout=subprocess.DEVNULL)
    with open(archive, "rb") as stream:
        archive_sha = digest(stream.read())
    with open(archive + ".sha256", "w", encoding="ascii") as stream:
        stream.write(f"{archive_sha}  {os.path.basename(archive)}\n")
    return archive


def restore_backup(archive):
    subprocess.run([
        "tar", "--numeric-owner", "--same-owner", "--same-permissions",
        "--acls", "--xattrs", "-xpf", archive, "-C", "/",
    ], check=True)


def prepare_target():
    info = require_regular_nonsymlink(TARGET)
    if info.st_nlink != 1:
        fail("refusing a hard-linked Advanced SD2 wrapper")
    with open(TARGET, "rb") as stream:
        original = stream.read()
    old_hash = digest(original)
    if old_hash in ALREADY_FIXED:
        return info, original, None, old_hash
    if old_hash not in TARGET_HASHES:
        fail(f"unrecognized/custom Advanced SD2 wrapper hash: {old_hash}")
    if original.count(ANCHOR) != 1:
        fail("the pinned stale Singe rewrite line is not present exactly once")
    repaired = original.replace(ANCHOR, b"", 1)
    expected = TARGET_HASHES[old_hash]
    if digest(repaired) != expected:
        fail("one-line removal did not produce its reviewed target hash")
    return info, original, repaired, expected


def copy_xattrs(source, destination):
    values = {name: os.getxattr(source, name, follow_symlinks=False)
              for name in os.listxattr(source, follow_symlinks=False)}
    for name, value in values.items():
        os.setxattr(destination, name, value, follow_symlinks=False)
    return values


def verify_xattrs(path, expected):
    actual = {name: os.getxattr(path, name, follow_symlinks=False)
              for name in os.listxattr(path, follow_symlinks=False)}
    if actual != expected:
        fail("extended attributes changed during the repair")


def surgical_rewrite(info, original, repaired, expected, backup):
    if repaired is None:
        print(f"{TARGET} already has the reviewed one-line repair ({expected}).")
        return
    old_hash = digest(original)
    # Recheck after backup creation so a concurrent/user edit is never replaced.
    if file_hash(TARGET) != old_hash:
        fail("Advanced SD2 wrapper changed while creating the rollback snapshot")
    xattrs = {name: os.getxattr(TARGET, name, follow_symlinks=False)
              for name in os.listxattr(TARGET, follow_symlinks=False)}

    parent = os.path.dirname(TARGET)
    fd, temporary = tempfile.mkstemp(prefix=".Switch-to-SD2-r4.", dir=parent)
    replaced = False
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(repaired)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, info.st_uid, info.st_gid)
        for name, value in xattrs.items():
            os.setxattr(temporary, name, value, follow_symlinks=False)
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        os.replace(temporary, TARGET)
        replaced = True
        dirfd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        if file_hash(TARGET) != expected:
            fail("installed Advanced SD2 wrapper hash does not match the reviewed result")
        after = os.stat(TARGET, follow_symlinks=False)
        if (after.st_uid, after.st_gid, stat.S_IMODE(after.st_mode)) != (
            info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)
        ):
            fail("numeric owner or mode changed during the repair")
        verify_xattrs(TARGET, xattrs)
        print(f"Repaired {TARGET}; rollback snapshot: {backup}")
    except Exception:
        if replaced:
            restore_backup(backup)
        raise
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_version_and_marker(backup):
    info = require_regular_nonsymlink(VERSION_FILE)
    with open(VERSION_FILE, "rb") as stream:
        previous_version = stream.read()
    if previous_version.strip() not in (b"10032026-r3", b"10032026-r4"):
        fail(".VERSION changed unexpectedly before the R4 commit")
    version_dir = os.path.dirname(VERSION_FILE)
    fd, temporary = tempfile.mkstemp(prefix=".VERSION.r4.", dir=version_dir)
    marker_created = False
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(b"10032026-r4\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, info.st_uid, info.st_gid)
        xattrs = copy_xattrs(VERSION_FILE, temporary)
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        with open(VERSION_FILE, "rb") as stream:
            if stream.read() != previous_version:
                fail(".VERSION changed concurrently during the R4 commit")
        os.replace(temporary, VERSION_FILE)
        verify_xattrs(VERSION_FILE, xattrs)
        after = os.stat(VERSION_FILE, follow_symlinks=False)
        if (after.st_uid, after.st_gid, stat.S_IMODE(after.st_mode)) != (
            info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)
        ):
            fail(".VERSION owner or mode changed during the R4 commit")
        dirfd = os.open(version_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        if os.path.lexists(DONE_MARKER):
            marker_info = os.lstat(DONE_MARKER)
            if not stat.S_ISREG(marker_info.st_mode):
                fail("R4 completion marker exists but is not a regular file")
        else:
            marker_fd = os.open(DONE_MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            marker_created = True
            try:
                os.fchown(marker_fd, info.st_uid, info.st_gid)
                os.fsync(marker_fd)
            finally:
                os.close(marker_fd)
        dirfd = os.open(version_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        print("R4 completion marker and .VERSION recorded.")
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        if marker_created and os.path.lexists(DONE_MARKER):
            os.unlink(DONE_MARKER)
        # The version is the last completed payload state before the marker;
        # restore just it if the two-file completion commit could not finish.
        subprocess.run([
            "tar", "--numeric-owner", "--same-owner", "--same-permissions",
            "--acls", "--xattrs", "-xpf", backup, "-C", "/",
            VERSION_FILE.lstrip("/"),
        ], check=True)
        raise


def main():
    if os.geteuid() != 0:
        fail("installer requires root")
    if len(sys.argv) != 2:
        fail("usage: install-r4.py roms|roms2")
    root_path = verify_active_rom_root(sys.argv[1])
    if os.path.lexists(TARGET):
        prepared = prepare_target()
    elif verified_safe_sd2_absence():
        prepared = None
        print("Advanced SD2 entry is absent in the verified SD2 state; Main-SD switching regenerates it from the clean canonical SD2 wrapper.")
    else:
        fail("Advanced SD2 entry is absent without a fully verified safe SD2 regeneration state")
    backup = make_backup(root_path, include_target=prepared is not None)
    if prepared is not None:
        surgical_rewrite(*prepared, backup)
    write_version_and_marker(backup)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"R4 installer: {error}", file=sys.stderr)
        sys.exit(1)
