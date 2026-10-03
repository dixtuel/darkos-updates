#!/usr/bin/env python3
"""Verify and apply the standalone PortMaster ARMhf compatibility bundle."""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


EXPECTED_ARCHIVE = "darkosupdate10032026-compat.zip"
EXPECTED_ARCHIVE_SHA256 = "86049c53e45c551078a260c346215f7254ea90cb0de967a124f0ae588625e8f7"
MAX_UNCOMPRESSED_BYTES = 16 * 1024 * 1024
SUPPORTED_VERSIONS = {
    "10032026": ".update10032026",
    "10032026-r1": ".update10032026-r1",
    "10032026-r2": ".update10032026-r2",
    "10032026-r3": ".update10032026-r3",
}
WEBPMUX_TARGETS = (
    ("usr/lib/arm-linux-gnueabihf/libwebpmux.so.3.0.1", "file",
     "247b24116480e9323e0c1d4870208aad3412d8b7bf5f4aad5fc3c4c48ed84cfc"),
    ("usr/lib/arm-linux-gnueabihf/libwebpmux.so.3", "symlink", "libwebpmux.so.3.0.1"),
)


class Refused(Exception):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member_name(name):
    if "\\" in name:
        raise Refused(f"ZIP member uses a backslash path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise Refused(f"unsafe ZIP member path: {name!r}")
    return name


def expected_member_names(manifest):
    packages = manifest.get("new_armhf_packages")
    if not isinstance(packages, list) or len(packages) != 26:
        raise Refused("bundle manifest does not describe the reviewed 26-package closure")
    names = {"install_armhf_closure.py", "package-manifest.json", "archive-review.json"}
    package_names = set()
    deb_names = set()
    for item in packages:
        package = item.get("Package")
        filename = item.get("Filename")
        if (not isinstance(package, str) or package in package_names or
                not isinstance(filename, str) or not PurePosixPath(filename).name):
            raise Refused("invalid or duplicate package entry in bundle manifest")
        basename = PurePosixPath(filename).name
        if basename in deb_names:
            raise Refused("duplicate package archive basename in bundle manifest")
        package_names.add(package)
        deb_names.add(basename)
        names.add("debs/" + basename)
        names.add("copyright/" + package + ".copyright")
    names.update({"webpmux/libwebpmux.so.3.0.1", "webpmux/libwebpmux.so.3"})
    return names


def inspect_bundle(archive, expected_sha256=EXPECTED_ARCHIVE_SHA256):
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_file():
        raise Refused("bundle ZIP must be a regular, non-symlink file")
    if expected_sha256 == "TO_BE_FILLED_AFTER_BUILD" or sha256_file(archive) != expected_sha256:
        raise Refused("bundle ZIP SHA-256 does not match the pinned feed checksum")
    try:
        with zipfile.ZipFile(archive, "r") as bundle:
            infos = bundle.infolist()
            member_names = [safe_member_name(info.filename) for info in infos]
            if len(member_names) != len(set(member_names)):
                raise Refused("bundle contains duplicate ZIP member names")
            if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
                raise Refused("bundle exceeds the uncompressed size limit")
            for info in infos:
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if info.is_dir() or kind not in (stat.S_IFREG, stat.S_IFLNK):
                    raise Refused(f"bundle member has an unsupported type: {info.filename}")
                if kind == stat.S_IFLNK:
                    if (info.filename != "webpmux/libwebpmux.so.3" or
                            stat.S_IMODE(mode) != 0o777 or
                            bundle.read(info).decode("utf-8") != "libwebpmux.so.3.0.1"):
                        raise Refused(f"bundle contains an unreviewed symlink: {info.filename}")
                elif stat.S_IMODE(mode) != 0o644:
                    raise Refused(f"bundle member has unexpected mode: {info.filename}")
                if info.flag_bits & 0x1:
                    raise Refused(f"encrypted ZIP member is unsupported: {info.filename}")
            manifest_data = bundle.read("package-manifest.json")
            manifest = json.loads(manifest_data)
            expected = expected_member_names(manifest)
            actual = set(member_names)
            if actual != expected:
                raise Refused(f"bundle member set mismatch; missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
            review = json.loads(bundle.read("archive-review.json"))
            if not isinstance(review, list) or len(review) != 26:
                raise Refused("bundle archive review does not contain 26 package records")
            review_by_package = {entry.get("package"): entry for entry in review}
            if len(review_by_package) != 26:
                raise Refused("bundle archive review has duplicate/missing package names")
            for item in manifest["new_armhf_packages"]:
                member = "debs/" + PurePosixPath(item["Filename"]).name
                info = bundle.getinfo(member)
                payload = bundle.read(member)
                if (len(payload) != int(item["Size"]) or
                        sha256_bytes(payload) != item["SHA256"]):
                    raise Refused(f"pinned package size/hash mismatch: {member}")
                review_entry = review_by_package.get(item["Package"])
                if (not review_entry or review_entry.get("version") != item["Version"] or
                        review_entry.get("architecture") != "armhf" or
                        review_entry.get("multi_arch") != "same"):
                    raise Refused(f"archive review does not match manifest package {item['Package']}")
            mux_object = bundle.read("webpmux/libwebpmux.so.3.0.1")
            mux_link = bundle.read("webpmux/libwebpmux.so.3").decode("utf-8")
            if (sha256_bytes(mux_object) != WEBPMUX_TARGETS[0][2] or
                    mux_link != WEBPMUX_TARGETS[1][2]):
                raise Refused("WebP mux object/link differs from reviewed R2 payload")
            bad = bundle.testzip()
            if bad is not None:
                raise Refused(f"ZIP CRC failure in {bad}")
            return manifest, infos
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, ValueError) as exc:
        raise Refused(f"cannot validate bundle ZIP: {exc}") from exc


def extract_verified(archive, stage, manifest, infos):
    stage = Path(stage)
    if stage.is_symlink() or not stage.is_dir() or any(stage.iterdir()):
        raise Refused("extraction staging directory must be an empty real directory")
    try:
        with zipfile.ZipFile(archive, "r") as bundle:
            for info in infos:
                relative = PurePosixPath(safe_member_name(info.filename))
                target = stage.joinpath(*relative.parts)
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if target.is_symlink() or os.path.lexists(target):
                    raise Refused(f"staging path already exists: {info.filename}")
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as output, bundle.open(info, "r") as source:
                    shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise Refused(f"safe ZIP extraction failed: {exc}") from exc


def validate_device_target():
    if os.geteuid() != 0:
        raise Refused("apply requires root")
    try:
        compatible = Path("/proc/device-tree/compatible").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
    except OSError as exc:
        raise Refused(f"cannot read device-tree compatibility: {exc}") from exc
    if "rk3326" not in compatible.lower():
        raise Refused(f"target is not an RK3326 device: {compatible.strip()!r}")
    version_path = Path("/home/ark/.config/.VERSION")
    if version_path.is_symlink() or not version_path.is_file():
        raise Refused("base .VERSION is missing or not a regular file")
    version = version_path.read_text(errors="replace").strip()
    marker = SUPPORTED_VERSIONS.get(version)
    marker_path = Path("/home/ark/.config", marker) if marker else None
    if marker is None or marker_path.is_symlink() or not marker_path.is_file():
        raise Refused(f"unsupported base .VERSION/update marker pair: {version!r}")


def run_helper(helper, deb_dir, apply):
    argv = [sys.executable, str(helper), "--deb-dir", str(deb_dir)]
    if apply:
        argv.append("--apply")
    env = os.environ.copy()
    env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    result = subprocess.run(argv, env=env, check=False)
    if result.returncode:
        raise Refused(f"package closure helper returned {result.returncode}")


def configured_rom_root(values, mounted):
    has_rom1 = any(value.startswith("/roms/") or value == "/roms" for value in values)
    has_rom2 = any(value.startswith("/roms2/") or value == "/roms2" for value in values)
    if has_rom1 == has_rom2:
        raise Refused("EmulationStation ROM paths are missing or ambiguous between /roms and /roms2")
    selected = "/roms2" if has_rom2 else "/roms"
    if selected not in mounted:
        raise Refused(f"EmulationStation uses {selected}, but that ROM card is not mounted")
    return selected


def mounted_rom_card():
    config = Path("/etc/emulationstation/es_systems.cfg")
    try:
        import re
        values = re.findall(r"<path>([^<]+)</path>", config.read_text(encoding="utf-8", errors="strict"))
    except OSError as exc:
        raise Refused(f"cannot read active EmulationStation ROM paths: {exc}") from exc
    mounted = {str(root) for root in (Path("/roms"), Path("/roms2"))
               if not root.is_symlink() and root.is_mount()}
    selected = configured_rom_root(values, mounted)
    root = Path(selected)
    if str(root) not in mounted:
        raise Refused(f"EmulationStation uses {root}, but that ROM card is not mounted")
    result = subprocess.run(["findmnt", "-n", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS", "--target", str(root)],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={**os.environ, "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"})
    fields = result.stdout.split()
    if (result.returncode != 0 or len(fields) != 4 or fields[0] != str(root) or
            "rw" not in fields[3].split(",")):
        raise Refused(f"configured ROM card {root} is not verifiably mounted read/write")
    return root, fields[1], fields[2]


def inspect_webpmux_target(relative, kind, expected):
    target = Path("/") / relative
    current = Path("/")
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if not os.path.lexists(current):
            raise Refused(f"WebP mux directory is missing: {current}")
        st = os.lstat(current)
        if not stat.S_ISDIR(st.st_mode):
            raise Refused(f"WebP mux directory ancestor is not a real directory: {current}")
    if target.is_symlink() and kind == "symlink":
        st = os.lstat(target)
        if os.readlink(target) != expected or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o777:
            raise Refused(f"unexpected existing WebP mux link or metadata: {target}")
        return {"path": "/" + relative, "exists": True, "type": "symlink", "link": expected,
                "mode": "0o777", "uid": st.st_uid, "gid": st.st_gid}
    if os.path.lexists(target):
        st = os.lstat(target)
        if kind != "file" or not stat.S_ISREG(st.st_mode):
            raise Refused(f"unexpected WebP mux target type: {target}")
        if sha256_file(target) != expected or stat.S_IMODE(st.st_mode) != 0o644 or st.st_uid != 0 or st.st_gid != 0:
            raise Refused(f"existing WebP mux file differs from the reviewed object: {target}")
        return {"path": "/" + relative, "exists": True, "type": "file", "sha256": expected,
                "mode": "0o755", "uid": 0, "gid": 0}
    return {"path": "/" + relative, "exists": False}


def checked_backup_directory(root):
    current = root
    for name in ("backup", "darkosre-update"):
        current = current / name
        if os.path.lexists(current):
            if current.is_symlink() or not current.is_dir():
                raise Refused(f"unsafe rollback directory component: {current}")
        else:
            current.mkdir()
    return current / "10032026-compat-webpmux"


def save_webpmux_backup(root, source, fstype, target_states):
    backup = checked_backup_directory(root)
    if backup.is_symlink():
        raise Refused("WebP mux rollback directory is a symlink")
    if backup.exists():
        state_path = backup / "rollback-state.json"
        tar_path = backup / "rollback.tar"
        if state_path.is_symlink() or tar_path.is_symlink() or not state_path.is_file() or not tar_path.is_file():
            raise Refused(f"incomplete existing WebP mux rollback bundle: {backup}")
        state = json.loads(state_path.read_text())
        before = state.get("before")
        if (state.get("active_rom_mount") != str(root) or state.get("mount_source") != source or
                state.get("filesystem") != fstype or not isinstance(before, list) or
                len(before) != len(target_states) or state.get("tar_sha256") != sha256_file(tar_path)):
            raise Refused(f"existing WebP mux rollback bundle does not match: {backup}")
        before_by_path = {item.get("path"): item for item in before}
        for current in target_states:
            original = before_by_path.get(current["path"])
            if original is None:
                raise Refused(f"rollback bundle misses WebP path state: {current['path']}")
            if original.get("exists"):
                if original != current:
                    raise Refused(f"pre-existing WebP path changed since rollback snapshot: {current['path']}")
            elif current.get("exists"):
                entry = next(x for x in WEBPMUX_TARGETS if "/" + x[0] == current["path"])
                if current != inspect_webpmux_target(*entry):
                    raise Refused(f"WebP path is not the reviewed installed object: {current['path']}")
        return backup
    backup.mkdir()
    relative_existing = [x["path"].lstrip("/") for x in target_states if x.get("exists")]
    tar_path = backup / "rollback.tar"
    tar_args = ["tar", "--numeric-owner", "--xattrs", "--acls", "-cpf", str(tar_path), "-C", "/"]
    tar_args += ["--", *relative_existing] if relative_existing else ["--files-from=/dev/null"]
    env = os.environ.copy()
    env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    result = subprocess.run(tar_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode:
        raise Refused(f"could not create WebP mux rollback tar: {result.stderr.decode(errors='replace').strip()}")
    with tarfile.open(tar_path, "r") as tar:
        tar.getmembers()
    state = {
        "active_rom_mount": str(root), "mount_source": source, "filesystem": fstype,
        "before": target_states, "tar_sha256": sha256_file(tar_path),
        "recovery": "Only remove a target that still matches the reviewed file hash or symlink target; then extract rollback.tar as root to restore paths that existed before installation. No package database restore or package removal is authorized.",
    }
    (backup / "rollback-state.json").write_text(json.dumps(state, indent=2) + "\n")
    (backup / "RECOVERY.txt").write_text(
        "WebP mux rollback snapshot for the two guarded ARMhf paths. Inspect rollback-state.json. "
        "Only remove paths that still match the reviewed payload, then restore pre-existing paths with `tar --numeric-owner -xpf rollback.tar -C /`. "
        "Do not restore dpkg status or remove compatibility packages.\n")
    return backup


def install_webpmux(stage, states):
    for relative, kind, expected in WEBPMUX_TARGETS:
        target = Path("/") / relative
        before = next(state for state in states if state["path"] == "/" + relative)
        current = inspect_webpmux_target(relative, kind, expected)
        if current.get("exists"):
            continue
        if before.get("exists"):
            raise Refused(f"WebP mux path disappeared after rollback snapshot: {target}")
        source = Path(stage) / "webpmux" / Path(relative).name
        if kind == "file":
            temp = target.parent / ("." + target.name + ".compat-" + str(os.getpid()))
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            try:
                with os.fdopen(fd, "wb") as output, open(source, "rb") as input_file:
                    shutil.copyfileobj(input_file, output)
                    output.flush()
                    os.fsync(output.fileno())
                os.chown(temp, 0, 0)
                os.chmod(temp, 0o644)
                if sha256_file(temp) != expected:
                    raise Refused("staged WebP mux object hash changed")
                os.link(temp, target)
            finally:
                if os.path.lexists(temp):
                    os.unlink(temp)
        else:
            os.symlink(expected, target)
        inspect_webpmux_target(relative, kind, expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="verified darkosupdate10032026-compat.zip")
    parser.add_argument("--verify-only", action="store_true", help="validate the archive without target checks or writes")
    args = parser.parse_args()
    try:
        if args.archive.name != EXPECTED_ARCHIVE:
            raise Refused(f"unexpected archive filename; expected {EXPECTED_ARCHIVE}")
        manifest, infos = inspect_bundle(args.archive)
        if args.verify_only:
            print(f"PASS bundle checksum and contents: {len(infos)} files, {sum(i.file_size for i in infos)} uncompressed bytes")
            return 0
        validate_device_target()
        stage_parent = Path(tempfile.gettempdir())
        stage_bytes = sum(info.file_size for info in infos) + 1024 * 1024
        if shutil.disk_usage(stage_parent).free < stage_bytes:
            raise Refused(f"temporary filesystem lacks space for guarded extraction; need {stage_bytes} bytes")
        stage = Path(tempfile.mkdtemp(prefix="portmaster-armhf-compat-"))
        try:
            extract_verified(args.archive, stage, manifest, infos)
            run_helper(stage / "install_armhf_closure.py", stage / "debs", apply=False)
            target_states = [inspect_webpmux_target(*entry) for entry in WEBPMUX_TARGETS]
            rom_root, source, fstype = mounted_rom_card()
            backup = save_webpmux_backup(rom_root, source, fstype, target_states)
            run_helper(stage / "install_armhf_closure.py", stage / "debs", apply=True)
            install_webpmux(stage, target_states)
            print(f"Compatibility packages and guarded WebP mux paths verified. WebP rollback: {backup}")
            print("No update marker, .VERSION, reboot, or package removal was performed.")
            return 0
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    except (Refused, OSError, ValueError, KeyError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
