#!/usr/bin/env python3
"""Test the updater's exact backup-retention functions in temporary cards."""

import hashlib
import json
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
source = (ROOT / "dArkOSUpdate.sh").read_text()
start = source.index("# BEGIN BACKUP_RETENTION\n") + len("# BEGIN BACKUP_RETENTION\n")
end = source.index("# END BACKUP_RETENTION\n", start)
functions = source[start:end]


def tree_digest(root):
    entries = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((rel, "symlink", str(path.readlink())))
        elif path.is_file():
            entries.append((rel, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        elif path.is_dir():
            entries.append((rel, "dir"))
    return entries


def make_common_snapshot(path):
    path.mkdir(parents=True)
    content = path / "before.txt"
    content.write_text("previous system state\n")
    archive = path / "rollback.tar"
    subprocess.run(["tar", "-cpf", str(archive), "-C", str(path), "before.txt"], check=True)
    subprocess.run(["sha256sum", "rollback.tar"], cwd=path, check=True,
                   stdout=(path / "rollback.sha256").open("w"))
    (path / "backup-ready").touch()


def make_compat_snapshot(path):
    path.mkdir(parents=True)
    content = path / "before.txt"
    content.write_text("previous webpmux state\n")
    archive = path / "rollback.tar"
    subprocess.run(["tar", "-cpf", str(archive), "-C", str(path), "before.txt"], check=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (path / "rollback-state.json").write_text(json.dumps({"tar_sha256": digest}) + "\n")


def make_r4_snapshot(path):
    path.mkdir(parents=True)
    content = path / "previous-version.txt"
    content.write_text("10032026-r3\n")
    archive = path / "advanced-sd2-wrapper.before.tar"
    subprocess.run(["tar", "-cpf", str(archive), "-C", str(path), "previous-version.txt"], check=True)
    subprocess.run(["sha256sum", archive.name], cwd=path, check=True,
                   stdout=(path / (archive.name + ".sha256")).open("w"))


def run_case(name, completed, latest, corrupt_latest=False, incomplete=(), unsafe=()):
    with tempfile.TemporaryDirectory(prefix="update-backup-retention-") as temp:
        base = pathlib.Path(temp)
        mount = base / "card"
        config = base / "config"
        backup_root = mount / "backup" / "darkosre-update"
        mock_bin = base / "mock-bin"
        mount.mkdir()
        config.mkdir()
        backup_root.mkdir(parents=True)
        mock_bin.mkdir()

        stage_names = (
            "10032026", "10032026-r1", "10032026-compat", "10032026-r2",
            "10032026-r3", "10032026-r4", "10032026-r5",
        )
        backup_names = {
            "10032026": "10032026",
            "10032026-r1": "10032026-r1",
            "10032026-compat": "10032026-compat-webpmux",
            "10032026-r2": "10032026-r2",
            "10032026-r3": "10032026-r3",
            "10032026-r4": "10032026-r4",
            "10032026-r5": "10032026-r5",
        }
        for stage in completed:
            marker = {
                "10032026": ".update10032026",
                "10032026-r1": ".update10032026-r1",
                "10032026-compat": ".update10032026-compat",
                "10032026-r2": ".update10032026-r2",
                "10032026-r3": ".update10032026-r3",
                "10032026-r4": ".update10032026-r4",
                "10032026-r5": ".update10032026-r5",
            }[stage]
            (config / marker).touch()

        for stage in stage_names:
            target = backup_root / backup_names[stage]
            if stage in unsafe:
                target.symlink_to(base / "outside")
            elif stage in completed or stage in incomplete:
                if stage == "10032026-compat":
                    make_compat_snapshot(target)
                elif stage == "10032026-r4":
                    make_r4_snapshot(target)
                else:
                    make_common_snapshot(target)
        unrelated = backup_root / "portmaster-armhf-closure-preserve"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("not an OTA rollback\n")

        if corrupt_latest and latest:
            latest_dir = backup_root / backup_names[latest]
            if latest == "10032026-compat":
                (latest_dir / "rollback-state.json").write_text('{"tar_sha256":"wrong"}\n')
            elif latest == "10032026-r4":
                (latest_dir / "advanced-sd2-wrapper.before.tar.sha256").write_text("bad hash\n")
            else:
                (latest_dir / "rollback.sha256").write_text("bad hash\n")

        sudo = mock_bin / "sudo"
        sudo.write_text("#!/bin/bash\n[[ \"$1\" == rm ]] || exit 99\nshift\ncommand rm \"$@\"\n")
        sudo.chmod(0o755)
        runner = base / "run.sh"
        runner.write_text(
            "#!/bin/bash\n"
            "LOG_FILE=\"$5\"\n"
            + functions
            + "\nprune_superseded_backups \"$1\" \"roms\" \"$2\" \"$3\"\n"
        )
        runner.chmod(0o755)
        result = subprocess.run(
            ["bash", str(runner), str(config), str(backup_root), str(mount), "", str(base / "cleanup.log")],
            env={"PATH": f"{mock_bin}:/usr/bin:/bin"}, capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError(f"{name}: rc={result.returncode} {result.stdout} {result.stderr}")

        remaining = {p.name for p in backup_root.iterdir()}
        expected = {"portmaster-armhf-closure-preserve"}
        if latest:
            expected.add(backup_names[latest])
        for stage in incomplete:
            expected.add(backup_names[stage])
        for stage in unsafe:
            expected.add(backup_names[stage])
        if corrupt_latest:
            expected.update(backup_names[stage] for stage in completed)
        if remaining != expected:
            raise AssertionError(f"{name}: expected remaining {expected}, got {remaining}")


run_case(
    "successful R4 removes superseded stages",
    ("10032026", "10032026-r1", "10032026-compat", "10032026-r2", "10032026-r3", "10032026-r4"),
    "10032026-r4",
)
run_case(
    "successful R5 keeps only newest verified rollback",
    ("10032026", "10032026-r1", "10032026-compat", "10032026-r2", "10032026-r3", "10032026-r4", "10032026-r5"),
    "10032026-r5",
)
run_case(
    "successful R2 keeps incomplete later backups",
    ("10032026", "10032026-r1", "10032026-compat", "10032026-r2"),
    "10032026-r2",
    incomplete=("10032026-r3",),
)
run_case(
    "unsafe older snapshot path is retained",
    ("10032026", "10032026-r1", "10032026-compat", "10032026-r2", "10032026-r3", "10032026-r4"),
    "10032026-r4",
    unsafe=("10032026-r3",),
)
run_case(
    "corrupt latest rollback preserves every completed snapshot",
    ("10032026", "10032026-r1", "10032026-compat", "10032026-r2"),
    "10032026-r2",
    corrupt_latest=True,
)
run_case("no completed marker preserves everything", (), None, incomplete=("10032026",))
print("Backup retention fixtures passed: verified latest snapshot, superseded pruning, incomplete preservation, and fail-closed corruption handling.")
