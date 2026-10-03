#!/usr/bin/env python3
"""Fail-closed local dpkg installer for the pinned PortMaster ARMhf closure.

Not wired to the raw updater. Default mode only audits; --apply performs one
explicit local dpkg transaction. --resume only replays archives from a backup
made by this helper. It never calls APT, an online repository, autoremove, or
package removal.
"""

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "package-manifest.json"
ARCHIVE_REVIEW = HERE / "archive-review.json"
ALLOWED_PARTIAL = {"unpacked", "half-installed", "half-configured", "triggers-awaited", "triggers-pending"}
VERSIONED = re.compile(r"^([a-z0-9][a-z0-9+.-]*)(?::([a-z0-9-]+))?(?:\s*\((<<|<=|=|>=|>>|<|>)\s*([^()]+)\))?$")
SYSTEM_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
REQUIRED_TOOLS = {
    "dpkg", "dpkg-deb", "dpkg-query", "findmnt", "ldconfig", "ps", "start-stop-daemon", "tar",
}


class GateError(Exception):
    pass


def run(args, *, capture=True, check=True):
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.PIPE if capture else None, env=command_environment())
    if check and p.returncode:
        details = (p.stderr or p.stdout or "").strip()
        raise GateError(f"command failed ({p.returncode}): {args[0]} {args[1:]}: {details}")
    return p


def command_environment():
    """Give dpkg and its maintainer scripts a stable system PATH under sudo."""
    env = os.environ.copy()
    env["PATH"] = SYSTEM_PATH
    return env


def missing_required_tools(available):
    return sorted(REQUIRED_TOOLS - set(available))


def require_required_tools():
    available = {name for name in REQUIRED_TOOLS if shutil.which(name, path=SYSTEM_PATH)}
    missing = missing_required_tools(available)
    if missing:
        raise GateError(f"required system tools are unavailable on controlled PATH {SYSTEM_PATH}: {missing}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_status_text(text):
    out = {}
    for paragraph in text.split("\n\n"):
        fields, key = {}, None
        for line in paragraph.splitlines():
            if not line:
                continue
            if line[0].isspace():
                if key:
                    fields[key] += "\n" + line
            elif ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.lstrip()
        if fields.get("Package") and fields.get("Architecture"):
            pair = (fields["Package"], fields["Architecture"])
            if pair in out:
                raise GateError(f"duplicate dpkg status record {pair[0]}:{pair[1]}")
            out[pair] = fields
    return out


def unrelated_status_changes(before, after, candidates):
    allowed = {(name, "armhf") for name in candidates}
    return sorted(pair for pair in set(before) | set(after)
                  if pair not in allowed and before.get(pair) != after.get(pair))


def current_status():
    path = Path("/var/lib/dpkg/status")
    text = path.read_text(encoding="utf-8", errors="strict")
    return text, parse_status_text(text)


def deb_control(deb):
    raw = run(["dpkg-deb", "-f", str(deb)]).stdout
    fields, key = {}, None
    for line in raw.splitlines():
        if line and line[0].isspace():
            if key:
                fields[key] += "\n" + line
        elif ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields


def archive_members(deb, member_type):
    option = "--ctrl-tarfile" if member_type == "control" else "--fsys-tarfile"
    p = subprocess.run(["dpkg-deb", option, str(deb)], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=command_environment())
    if p.returncode:
        raise GateError(f"dpkg-deb {option} failed: {deb}: {p.stderr.decode(errors='replace')}")
    return tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:")


def read_control_tar(deb):
    with archive_members(deb, "control") as tf:
        files = {}
        for m in tf.getmembers():
            name = m.name.lstrip("./")
            if m.isfile() and name in {"control", "preinst", "postinst", "prerm", "postrm", "triggers", "conffiles"}:
                files[name] = tf.extractfile(m).read().decode("utf-8", errors="replace")
    return files


def control_file_hashes(deb):
    with archive_members(deb, "control") as tf:
        return {
            m.name.lstrip("./"): hashlib.sha256(tf.extractfile(m).read()).hexdigest()
            for m in tf.getmembers() if m.isfile()
        }


def normalize_payload_path(member):
    name = member.name
    while name.startswith("./"):
        name = name[2:]
    if name in ("", ".") and member.isdir():
        return "/"
    if name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/")):
        raise GateError(f"unsafe archive member path: {member.name!r}")
    return "/" + name


def installed_version_satisfies(actual, relation, wanted):
    if not wanted:
        return True
    op = {"<": "lt", "<<": "lt", "<=": "le", "=": "eq", ">=": "ge", ">": "gt", ">>": "gt"}[relation]
    return run(["dpkg", "--compare-versions", actual, op, wanted], check=False).returncode == 0


def installed_for_dependency(records, name, candidate_versions):
    if name in candidate_versions:
        return candidate_versions[name]
    for arch in ("armhf", "all"):
        rec = records.get((name, arch))
        if rec and rec.get("Status") == "install ok installed":
            return rec.get("Version")
    # An unqualified dependency can be satisfied by a foreign package only
    # when its installed control declares Multi-Arch: foreign.
    rec = records.get((name, "arm64"))
    if rec and rec.get("Status") == "install ok installed" and rec.get("Multi-Arch") == "foreign":
        return rec.get("Version")
    return None


def check_relations(field, records, candidates, package, label):
    if not field:
        return
    for term in field.split(","):
        term = term.strip()
        if "|" in term:
            raise GateError(f"unsupported alternative relation in {package} {label}: {term}")
        match = VERSIONED.fullmatch(term)
        if not match:
            raise GateError(f"unsupported Debian relation in {package} {label}: {term}")
        name, arch_qual, relation, wanted = match.groups()
        if arch_qual not in (None, "armhf"):
            raise GateError(f"unsupported architecture qualifier in {term}")
        actual = installed_for_dependency(records, name, candidates)
        if label in ("Conflicts", "Breaks"):
            installed = [r for (n, _a), r in records.items() if n == name and r.get("Status") == "install ok installed"]
            if any(not relation or installed_version_satisfies(r.get("Version", "0"), relation, wanted) for r in installed):
                raise GateError(f"installed package conflicts with candidate: {package} {label} {term}")
        elif actual is None or (relation and not installed_version_satisfies(actual, relation, wanted)):
            raise GateError(f"unsatisfied {label} dependency for {package}: {term}")


def check_replaces(field, records, package):
    """Only permit reviewed Replaces when no named package has any live record."""
    if not field:
        return
    for term in field.split(","):
        term = term.strip()
        match = VERSIONED.fullmatch(term)
        if not match or "|" in term:
            raise GateError(f"unsupported Replaces relation in {package}: {term}")
        name, arch_qual, _relation, _wanted = match.groups()
        if arch_qual not in (None, "armhf"):
            raise GateError(f"unsupported Replaces architecture qualifier in {term}")
        records_present = [(arch, rec) for arch, rec in all_records_by_name(records, name)
                           if rec.get("Status", "").split()[-1:] != ["not-installed"]]
        if records_present:
            pairs = [f"{name}:{arch}={rec.get('Version')} ({rec.get('Status')})"
                     for arch, rec in records_present]
            raise GateError(f"Replaces target already has a dpkg record; refusing file takeover: {pairs}")


def all_records_by_name(records, name):
    return [(arch, rec) for (pkg, arch), rec in records.items() if pkg == name]


def audit_is_clean(records, candidates, resume):
    audit = run(["dpkg", "--audit"], check=False)
    if not audit.returncode and not audit.stdout.strip() and not audit.stderr.strip():
        return True
    if not resume:
        raise GateError("dpkg --audit is not clean; repair package state before this update")
    # A resume may have only exact pinned candidates in a recognized partial
    # state. Any unrelated or unexpected package state remains a hard stop.
    for (name, arch), rec in records.items():
        status = rec.get("Status", "")
        if status.split()[-1:] in (["installed"], ["config-files"], ["not-installed"]):
            continue
        if (name in candidates and arch == "armhf" and
                rec.get("Version") == candidates[name] and
                status in {"install ok " + state for state in ALLOWED_PARTIAL}):
            continue
        raise GateError(f"dpkg audit found unrelated/ineligible package state: {name}:{arch} {status!r}")
    return True


def parse_dpkg_owners(output, package):
    """Accept only same-name arm64/armhf owners; reject ambiguous/foreign owners."""
    owners = set()
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if ": " not in line:
            raise GateError(f"unrecognized dpkg-query -S output: {line}")
        owner_list, _path = line.rsplit(": ", 1)
        for owner in owner_list.split(","):
            owner = owner.strip()
            if ":" not in owner:
                raise GateError(f"unqualified dpkg owner is ambiguous: {line}")
            name, arch = owner.rsplit(":", 1)
            if name != package or arch not in {"arm64", "armhf"}:
                raise GateError(f"path has unrelated/unsupported owner: {line}")
            owners.add(arch)
    if not owners:
        raise GateError("path has no dpkg owner")
    return owners


def check_existing_ancestors(path):
    allowed_usrmerge = {
        "/bin": "usr/bin", "/sbin": "usr/sbin", "/lib": "usr/lib",
        "/lib32": "usr/lib32", "/lib64": "usr/lib64", "/libx32": "usr/libx32",
    }
    current = Path("/")
    for part in Path(path).parts[1:-1]:
        current = current / part
        if not os.path.lexists(current):
            break
        st = os.lstat(current)
        if stat.S_ISLNK(st.st_mode):
            if str(current) not in allowed_usrmerge or os.readlink(current) != allowed_usrmerge[str(current)]:
                raise GateError(f"unexpected symlink ancestor: {current} -> {os.readlink(current)}")
        elif not stat.S_ISDIR(st.st_mode):
            raise GateError(f"non-directory ancestor: {current}")


def inspect_inputs(deb_dir, manifest, archive_review):
    review = {x["package"]: x for x in archive_review}
    candidates = {x["Package"]: x["Version"] for x in manifest["new_armhf_packages"]}
    debs = {}
    for item in manifest["new_armhf_packages"]:
        deb = deb_dir / Path(item["Filename"]).name
        if deb.is_symlink() or not deb.is_file():
            raise GateError(f"missing pinned archive: {deb.name}")
        if deb.stat().st_size != int(item["Size"]) or sha256(deb) != item["SHA256"]:
            raise GateError(f"size/hash mismatch: {deb.name}")
        fields = deb_control(deb)
        expected = {"Package": item["Package"], "Version": item["Version"], "Architecture": "armhf", "Multi-Arch": "same"}
        for key, want in expected.items():
            if fields.get(key, "") != want:
                raise GateError(f"{deb.name}: {key} mismatch ({fields.get(key)!r}, expected {want!r})")
        if " ".join(fields.get("Depends", "").split()) != " ".join(item.get("Depends", "").split()):
            raise GateError(f"{deb.name}: Depends differs from pinned manifest")
        if fields["Package"] not in review:
            raise GateError(f"no actual archive review for {fields['Package']}")
        reviewed = review[fields["Package"]]
        for control_key, review_key in (
            ("Pre-Depends", "pre_depends"), ("Conflicts", "conflicts"),
            ("Breaks", "breaks"), ("Replaces", "replaces"),
        ):
            actual = " ".join(fields.get(control_key, "").split()) or None
            expected_value = " ".join((reviewed.get(review_key) or "").split()) or None
            if actual != expected_value:
                raise GateError(f"{deb.name}: {control_key} differs from actual archive review")
        if control_file_hashes(deb) != review[fields["Package"]].get("control_files_sha256"):
            raise GateError(f"control archive differs from preserved maintainer/trigger review: {deb.name}")
        controls = read_control_tar(deb)
        unexpected = set(controls) - {"control", "postinst", "triggers", "conffiles"}
        if unexpected:
            raise GateError(f"unreviewed control scripts/files in {deb.name}: {sorted(unexpected)}")
        if fields["Package"] == "libgcrypt20":
            postinst = controls.get("postinst", "")
            if "if [ -n \"$2\" ]" not in postinst or "clean-up-unmanaged-libraries" not in postinst:
                raise GateError("libgcrypt20 postinst differs from reviewed upgrade-gated cleanup")
        elif "postinst" in controls:
            raise GateError(f"unreviewed postinst in {deb.name}")
        triggers = [line.strip() for line in controls.get("triggers", "").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        if triggers != ["activate-noawait ldconfig"]:
            raise GateError(f"unexpected package triggers in {deb.name}")
        expected_conf = "/etc/vdpau_wrapper.cfg\n" if fields["Package"] == "libvdpau1" else None
        if controls.get("conffiles") != expected_conf:
            raise GateError(f"unreviewed conffile list in {deb.name}")
        # Retain all package control fields for native relation checks below.
        if fields["Package"] in debs:
            raise GateError(f"duplicate candidate package: {fields['Package']}")
        debs[fields["Package"]] = (deb, fields, candidates[fields["Package"]])
    extra = {p.name for p in deb_dir.glob("*.deb")} - {d.name for d, _f, _v in debs.values()}
    if extra:
        raise GateError(f"unexpected extra .deb files: {sorted(extra)}")
    return debs, candidates


def classify_packages(records, candidates, resume):
    add = []
    for name, version in candidates.items():
        current = records.get((name, "armhf"))
        if current is None:
            add.append(name)
        elif current.get("Version") == version and current.get("Status") == "install ok installed":
            pass
        elif resume and current.get("Version") == version and current.get("Status") in {"install ok " + state for state in ALLOWED_PARTIAL}:
            add.append(name)
        else:
            raise GateError(f"refusing {name}:armhf state/version {current.get('Status')!r}/{current.get('Version')!r}; expected absent or exact installed" + ("/reviewed partial state" if resume else ""))
        # Multi-Arch: same requires every installed architecture to have the
        # exact same version. A removal/config-files state is not treated as absent.
        for arch, rec in all_records_by_name(records, name):
            if arch == "armhf":
                continue
            if rec.get("Status") != "install ok installed" or rec.get("Version") != version:
                raise GateError(f"Multi-Arch: same mismatch for {name}:{arch}: {rec.get('Status')!r}/{rec.get('Version')!r}; expected installed {version}")
    return add


def verify_payload_collisions(debs, records, resume, resumable_additions):
    for name, (deb, _fields, version) in debs.items():
        expected_members = {x["path"]: x for x in next(v for v in json.loads(ARCHIVE_REVIEW.read_text()) if v["package"] == name)["payload"]}
        with archive_members(deb, "data") as tf:
            for member in tf.getmembers():
                path = normalize_payload_path(member)
                kind = "dir" if member.isdir() else "file" if member.isfile() else "symlink" if member.issym() else "other"
                record = expected_members.get(path)
                if record is None or record["type"] != kind:
                    raise GateError(f"payload differs from reviewed archive: {name} {path}")
                if record.get("mode") != oct(member.mode) or record.get("uid") != member.uid or record.get("gid") != member.gid:
                    raise GateError(f"archive metadata differs from review record: {name} {path}")
                if kind == "other":
                    raise GateError(f"unsupported special payload member: {name} {path}")
                if kind == "file":
                    reviewed_hash = hashlib.sha256(tf.extractfile(member).read()).hexdigest()
                    if record.get("sha256") != reviewed_hash:
                        raise GateError(f"archive content differs from review record: {name} {path}")
                if kind == "symlink" and record.get("link") != member.linkname:
                    raise GateError(f"archive symlink differs from review record: {name} {path}")
                check_existing_ancestors(path)
                if not os.path.lexists(path):
                    continue
                st = os.lstat(path)
                if kind == "dir":
                    if not stat.S_ISDIR(st.st_mode):
                        raise GateError(f"directory collision: {path}")
                    continue
                if kind == "file" and not stat.S_ISREG(st.st_mode):
                    raise GateError(f"file type collision: {path}")
                if kind == "symlink" and not stat.S_ISLNK(st.st_mode):
                    raise GateError(f"symlink type collision: {path}")
                if kind == "file":
                    target_hash = sha256(path)
                    archive_hash = hashlib.sha256(tf.extractfile(member).read()).hexdigest()
                    if target_hash != archive_hash:
                        raise GateError(f"existing file differs from pinned package: {path}")
                elif os.readlink(path) != member.linkname:
                    raise GateError(f"existing symlink differs from pinned package: {path}")
                if stat.S_IMODE(st.st_mode) != member.mode or st.st_uid != member.uid or st.st_gid != member.gid:
                    raise GateError(f"existing file metadata differs from pinned package: {path}")
                owner_output = run(["dpkg-query", "-S", path], check=False).stdout
                if not owner_output.strip():
                    # An interrupted unpack may have placed a file before dpkg
                    # wrote the package file list. Only accept this when this
                    # exact package was absent in the helper's saved baseline
                    # and is currently in one of the explicitly allowed partial
                    # states. Normal preflight never accepts an ownerless file.
                    package_state = records.get((name, "armhf"), {})
                    if not (resume and name in resumable_additions and
                            package_state.get("Status") in {"install ok " + s for s in ALLOWED_PARTIAL} and
                            package_state.get("Version") == version):
                        raise GateError(f"existing path has unknown dpkg owner: {path}")
                    continue
                owners = parse_dpkg_owners(owner_output, name)
                valid_states = {"install ok installed"}
                if resume:
                    valid_states.update("install ok " + state for state in ALLOWED_PARTIAL)
                for arch in owners:
                    installed = records.get((name, arch))
                    if not installed or installed.get("Status") not in valid_states or installed.get("Version") != version:
                        raise GateError(f"existing path owner version/state mismatch: {path} ({arch})")


def configured_rom_root(paths, mounted_roots):
    """Require one ES ROM root and its real mount; never prefer SD2 by order."""
    has_rom2 = any(value.startswith("/roms2/") or value == "/roms2" for value in paths)
    has_rom1 = any(value.startswith("/roms/") or value == "/roms" for value in paths)
    if has_rom2 == has_rom1:
        raise GateError("EmulationStation ROM paths are missing or ambiguous between /roms and /roms2")
    expected = "/roms2" if has_rom2 else "/roms"
    if expected not in mounted_roots:
        raise GateError(f"EmulationStation uses {expected}, but that ROM card is not mounted")
    return expected


def active_card():
    config = Path("/etc/emulationstation/es_systems.cfg")
    try:
        text = config.read_text(encoding="utf-8", errors="strict")
    except OSError as exc:
        raise GateError(f"cannot read active EmulationStation system paths: {exc}") from exc
    configured_paths = re.findall(r"<path>([^<]+)</path>", text)
    mounted = {str(Path(p)) for p in ("/roms", "/roms2")
               if not Path(p).is_symlink() and Path(p).is_mount()}
    selected = configured_rom_root(configured_paths, mounted)
    p = Path(selected)
    if p.is_symlink() or not p.is_mount():
        raise GateError(f"configured ROM root is not a real mount: {selected}")
    line = run(["findmnt", "-n", "-o", "TARGET,SOURCE,FSTYPE", "--target", selected]).stdout.strip()
    fields = line.split()
    if len(fields) != 3 or fields[0] != selected:
        raise GateError(f"configured ROM card {selected} cannot be verified by findmnt")
    # Prove the mounted filesystem accepts writes; permission-bit checks alone
    # do not detect a read-only mount.
    fd, probe = tempfile.mkstemp(prefix=".portmaster-closure-writecheck-", dir=selected)
    os.close(fd)
    os.unlink(probe)
    return selected, fields[1], fields[2]


def checked_backup_root(root):
    current = Path(root)
    for child in ("backup", "darkosre-update"):
        current = current / child
        if os.path.lexists(current):
            st = os.lstat(current)
            if not stat.S_ISDIR(st.st_mode):
                raise GateError(f"backup path component is not a real directory: {current}")
        else:
            current.mkdir()
    return current


def make_backup(deb_dir, debs, status_text, actions, manifest_path, review_path):
    root, source, fstype = active_card()
    root_options = set(run(["findmnt", "-n", "-o", "OPTIONS", "--target", "/"]).stdout.strip().split(","))
    if "ro" in root_options:
        raise GateError("root filesystem is read-only")
    deb_bytes = sum(deb.stat().st_size for deb, _fields, _version in debs.values())
    reserve = deb_bytes + len(status_text.encode()) + 32 * 1024 * 1024
    if shutil.disk_usage(root).free < reserve:
        raise GateError(f"active ROM card lacks backup space; need at least {reserve} bytes free")
    root_free = shutil.disk_usage("/").free
    installed_bytes = sum(int(fields["Installed-Size"]) for _deb, fields, _version in debs.values()) * 1024
    root_reserve = installed_bytes + 16 * 1024 * 1024
    if root_free < root_reserve:
        raise GateError(f"root filesystem lacks package space; need at least {root_reserve} bytes free")
    backup = checked_backup_root(root) / ("portmaster-armhf-closure-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True, exist_ok=False)
    local_debs = backup / "debs"
    local_debs.mkdir()
    for deb, _fields, _version in debs.values():
        shutil.copy2(deb, local_debs / deb.name)
    shutil.copy2(Path(__file__), backup / "install_armhf_closure.py")
    shutil.copy2(manifest_path, backup / "package-manifest.json")
    shutil.copy2(review_path, backup / "archive-review.json")
    status_copy = backup / "dpkg-status.before"
    status_copy.write_text(status_text, encoding="utf-8")
    metadata = ["/var/lib/dpkg/status", "/var/log/dpkg.log"]
    for candidate in ("/var/lib/dpkg/status-old", "/var/lib/dpkg/available", "/var/lib/dpkg/triggers/File", "/var/lib/dpkg/triggers/Unincorp"):
        if os.path.isfile(candidate):
            metadata.append(candidate)
    for name in debs:
        for p in Path("/var/lib/dpkg/info").glob(name + ":armhf.*"):
            if p.is_file():
                metadata.append(str(p))
    # Save the existing shared files that passed the exact-content collision
    # guard. These are evidence/recovery copies, not a license to replace dpkg state.
    members = []
    for name, (deb, _fields, _version) in debs.items():
        with archive_members(deb, "data") as tf:
            for m in tf.getmembers():
                path = normalize_payload_path(m)
                if os.path.lexists(path) and not m.isdir():
                    members.append(path.lstrip("/"))
    metadata.extend(p.lstrip("/") for p in members)
    relative = sorted({p.lstrip("/") for p in metadata if os.path.lexists("/" + p.lstrip("/"))})
    tarpath = backup / "preinstall-files-and-dpkg-metadata.tar"
    run(["tar", "--numeric-owner", "--xattrs", "--acls", "-cpf", str(tarpath), "-C", "/", *relative])
    info = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "active_mount": root,
        "source": source,
        "filesystem": fstype,
        "dpkg_status_sha256": hashlib.sha256(status_text.encode()).hexdigest(),
        "candidate_archives": {n: {"file": d.name, "sha256": sha256(d)} for n, (d, _f, _v) in debs.items()},
        "installer_sha256": sha256(backup / "install_armhf_closure.py"),
        "package_manifest_sha256": sha256(backup / "package-manifest.json"),
        "archive_review_sha256": sha256(backup / "archive-review.json"),
        "actions": actions,
        "metadata_tar_sha256": sha256(tarpath),
        "recovery": "Keep the packages installed. If dpkg is interrupted, rerun this helper with --resume BACKUP_DIR to replay the exact bundled archives. Never untar this snapshot over / or restore dpkg status; it is evidence and a preinstall file backup, not an offline database rollback.",
    }
    (backup / "backup-manifest.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    (backup / "RECOVERY.txt").write_text(
        "No automatic package removal is performed. For an interrupted transaction, keep this directory and rerun the exact local transaction with:\n"
        f"  python3 '{backup / 'install_armhf_closure.py'}' --resume '{backup}' --apply\n"
        "This rechecks every archive, installed version, dependency, and path before it resumes. Do not restore dpkg-status.before over the live dpkg database.\n",
        encoding="utf-8",
    )
    return backup


def package_manager_idle():
    active = {"apt", "apt-get", "dpkg", "aptitude", "packagekitd"}
    names = run(["ps", "-eo", "comm="]).stdout.splitlines()
    busy = sorted({n.strip() for n in names if n.strip() in active or
                   n.strip().startswith(("apt.", "dpkg.", "unattended"))})
    if busy:
        raise GateError(f"package manager process is active: {busy}")


def validate_resume_directory(backup, candidates, manifest):
    if backup.is_symlink() or not backup.is_dir():
        raise GateError(f"resume directory does not exist: {backup}")
    manifest_file = backup / "backup-manifest.json"
    status_file = backup / "dpkg-status.before"
    if (manifest_file.is_symlink() or status_file.is_symlink() or
            not manifest_file.is_file() or not status_file.is_file()):
        raise GateError("resume directory lacks its helper backup manifest/status")
    if (backup / "debs").is_symlink() or not (backup / "debs").is_dir():
        raise GateError("resume backup has no real debs directory")
    info = json.loads(manifest_file.read_text(encoding="utf-8"))
    for relative, key in (("install_armhf_closure.py", "installer_sha256"),
                          ("package-manifest.json", "package_manifest_sha256"),
                          ("archive-review.json", "archive_review_sha256"),
                          ("preinstall-files-and-dpkg-metadata.tar", "metadata_tar_sha256")):
        path = backup / relative
        if path.is_symlink() or not path.is_file() or info.get(key) != sha256(path):
            raise GateError(f"resume backup integrity check failed: {relative}")
    before = status_file.read_text(encoding="utf-8")
    if hashlib.sha256(before.encode()).hexdigest() != info.get("dpkg_status_sha256"):
        raise GateError("saved pre-install dpkg status does not match backup manifest")
    baseline = parse_status_text(before)
    actions = set(info.get("actions", []))
    if not actions <= set(candidates):
        raise GateError("backup action list includes an unknown package")
    for name in actions:
        if (name, "armhf") in baseline:
            raise GateError(f"backup baseline shows {name}:armhf was not absent; refusing resume")
    manifest_files = {x["Package"]: Path(x["Filename"]).name for x in manifest["new_armhf_packages"]}
    for name in candidates:
        archive_info = info.get("candidate_archives", {}).get(name)
        deb = backup / "debs" / manifest_files[name]
        if not archive_info or not deb.is_file() or archive_info.get("sha256") != sha256(deb):
            raise GateError(f"resume archive missing or changed for {name}")
    return actions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--deb-dir", type=Path, help="directory containing exactly the 26 pinned .deb files")
    ap.add_argument("--apply", action="store_true", help="apply after all fail-closed checks and backup")
    ap.add_argument("--resume", type=Path, help="resume from a prior helper backup's debs/ directory")
    args = ap.parse_args()
    try:
        if os.geteuid() != 0 and args.apply:
            raise GateError("--apply requires the updater's root context")
        if args.resume:
            deb_dir = args.resume / "debs"
            if args.deb_dir:
                raise GateError("use either --deb-dir or --resume")
        elif args.deb_dir:
            deb_dir = args.deb_dir
        else:
            raise GateError("supply --deb-dir or --resume")
        manifest_path = args.resume / "package-manifest.json" if args.resume else MANIFEST
        review_path = args.resume / "archive-review.json" if args.resume else ARCHIVE_REVIEW
        # Check sbin tools before creating the recovery directory; sudo may
        # otherwise leave out ldconfig/start-stop-daemon used during configure.
        require_required_tools()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        review = json.loads(review_path.read_text(encoding="utf-8"))
        debs, candidates = inspect_inputs(deb_dir, manifest, review)
        original_actions = validate_resume_directory(args.resume, candidates, manifest) if args.resume else set()
        status_text, records = current_status()
        primary = run(["dpkg", "--print-architecture"]).stdout.strip()
        foreign = set(run(["dpkg", "--print-foreign-architectures"]).stdout.split())
        if primary != "arm64" or "armhf" not in foreign:
            raise GateError(f"wrong multiarch target: primary={primary}, foreign={sorted(foreign)}")
        audit_is_clean(records, candidates, bool(args.resume))
        additions = classify_packages(records, candidates, bool(args.resume))
        for name, (_deb, fields, _version) in debs.items():
            check_relations(fields.get("Pre-Depends"), records, candidates, name, "Pre-Depends")
            check_relations(fields.get("Depends"), records, candidates, name, "Depends")
            check_relations(fields.get("Conflicts"), records, candidates, name, "Conflicts")
            check_relations(fields.get("Breaks"), records, candidates, name, "Breaks")
            check_replaces(fields.get("Replaces"), records, name)
        if args.resume and not set(additions) <= original_actions:
            raise GateError(f"resume would install packages absent from the original backup action list: {sorted(set(additions)-original_actions)}")
        verify_payload_collisions(debs, records, bool(args.resume), set(additions) if args.resume else set())
        print(f"Preflight passed: {len(candidates)} pinned ARMhf packages; {len(additions)} to install/configure; {len(candidates)-len(additions)} already exact and installed.")
        print("No APT sources were read. No upgrade, removal, or file extraction was requested.")
        if not args.apply:
            print("CHECK ONLY: no package or device file was changed.")
            return 0
        package_manager_idle()
        # The raw updater caller is responsible for serializing updater runs.
        # This helper does not pre-acquire or claim to verify dpkg's lock; dpkg
        # obtains its own package database lock when the child transaction starts.
        locked_status_text, _locked_records = current_status()
        if hashlib.sha256(locked_status_text.encode()).hexdigest() != hashlib.sha256(status_text.encode()).hexdigest():
            raise GateError("dpkg status changed after preflight; rerun preflight")
        backup = args.resume if args.resume else make_backup(deb_dir, debs, status_text, additions, manifest_path, review_path)
        transaction = [str(debs[n][0]) for n in additions]
        if transaction:
            log = backup / "dpkg-install.log"
            with log.open("a", encoding="utf-8") as out:
                out.write("\n--- " + datetime.now().isoformat(timespec="seconds") + " ---\n")
                p = subprocess.run(["dpkg", "--install", *transaction], stdout=out,
                                   stderr=subprocess.STDOUT, text=True,
                                   env=command_environment())
            if p.returncode:
                raise GateError(f"dpkg transaction failed; marker must remain unset. Retain {backup}; recovery instructions are in RECOVERY.txt")
        after_text, after = current_status()
        unrelated = unrelated_status_changes(records, after, candidates)
        if unrelated:
            raise GateError(f"dpkg status changed outside the pinned ARMhf candidates: {unrelated}; marker must remain unset")
        incomplete = [n for n, v in candidates.items() if not ((rec := after.get((n, "armhf"))) and rec.get("Status") == "install ok installed" and rec.get("Version") == v)]
        if incomplete:
            raise GateError(f"packages not fully installed at exact versions: {incomplete}; marker must remain unset. Retain {backup} and resume from it.")
        audit = run(["dpkg", "--audit"], check=False)
        if audit.returncode or audit.stdout.strip() or audit.stderr.strip():
            raise GateError(f"dpkg audit failed after transaction; marker must remain unset. Retain {backup} and resume from it.")
        print(f"Package transaction complete. Backup: {backup}")
        print("This helper does not set the OTA marker, reboot, or claim PortMaster/gameplay validation.")
        return 0
    except (GateError, OSError, ValueError, KeyError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
