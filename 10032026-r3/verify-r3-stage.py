#!/usr/bin/env python3
"""Recheck the staged R3 package, guards, marker flow, and host fixtures."""
import hashlib
import json
import pathlib
import subprocess
import tempfile
import zipfile


stage = pathlib.Path(__file__).resolve().parent
update_repo = stage.parent
project = stage.parents[2]
archive = stage / "darkosupdate10032026-r3.zip"
digest = "f6123c9e3a7e95d58b7ca95c7fd653134fac1f5c8236427f2da6637de7755b87"
source_archive = project / "build/validation/ota-review-20261003/runtime-r3-device-candidate.zip"
updater = update_repo / "dArkOSUpdate.sh"
draft = update_repo / "drafts/next-ota-ppsspp-defaults"
manifest = json.loads((draft / "manifest.json").read_text())
source_root = project / "repositories/firmware-fork/files/ROOTFS"

assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
assert hashlib.sha256(source_archive.read_bytes()).hexdigest() == digest
assert (stage / "SHA256SUMS").read_text() == f"{digest}  {archive.name}\n"
assert len(manifest) == 19
expected_paths = {row["installed_path"] for row in manifest} | {"install-runtime.sh"}
with zipfile.ZipFile(archive) as payload:
    assert payload.testzip() is None
    assert set(payload.namelist()) == expected_paths
    for row in manifest:
        name = row["installed_path"]
        if row["kind"] == "symlink":
            assert payload.read(name).decode() == row["target"], name
            source = source_root / name
            mirror = draft / "payload" / name
            assert source.is_symlink() and mirror.is_symlink()
            assert source.readlink() == mirror.readlink() == pathlib.Path(row["target"])
        else:
            assert hashlib.sha256(payload.read(name)).hexdigest() == row["sha256"], name
            source = source_root / name
            mirror = draft / "payload" / name
            assert source.read_bytes() == mirror.read_bytes() == payload.read(name), name
    assert payload.read("install-runtime.sh") == (draft / "install-runtime.sh").read_bytes()

subprocess.run(
    ["python3", str(update_repo / "tools/validate-current-ota.py"), str(archive)],
    cwd=project,
    check=True,
)
subprocess.run(["bash", "-n", str(updater)], check=True)

text = updater.read_text()
header = text.split('if [ -f "$LOG_FILE" ]; then', 1)[0]
assert 'R3_UPDATE_DONE="$CONFIG_DIR/.update10032026-r3"' in header
assert 'COMPAT_UPDATE_DONE="$CONFIG_DIR/.update10032026-compat"' in header
assert 'CURRENT_VERSION="$(tr -d' in header
assert 'Unsupported firmware version' in header
assert 'NEXT_STAGE="10032026-r3"' in text
r2 = text.split('PATCH_VERSION="10032026-r2"', 1)[1].split('PATCH_VERSION="10032026-r3"', 1)[0]
r3 = text.split('PATCH_VERSION="10032026-r3"', 1)[1].split('PATCH_VERSION="10032026-r4"', 1)[0]
for block in (r2, r3):
    assert 'if [ "$INSTALL_STATUS" -ne 0 ]; then exit "$INSTALL_STATUS"; fi' in block
    assert 'exit "$INSTALL_STATUS"' in block
    assert 'exit 187' not in block
assert 'R2 completed successfully; continuing to the next missing update in this run.' in r2
assert 'R3 completed successfully; continuing to R4 in this run.' in r3
assert 'sudo bash "$INSTALLER" "$UPDATE_ZIP" "$UPDATE_SHA256"' in r3
assert '[[ "$BASE_VERSION" != "10032026-r2" ]]' in r3
assert '[ ! -f "/home/ark/.config/.update10032026-r2" ]' in r3
assert f'UPDATE_SHA256="{digest}"' in r3
assert 'UPDATE_URL="$LOCATION/$PATCH_VERSION/darkosupdate$PATCH_VERSION.zip"' in r3

subprocess.run(
    ["python3", str(update_repo / "tools/verify-update-sequence.py")],
    cwd=update_repo,
    check=True,
)

fixture = project / "build/validation/ota-review-20261003/host-fixture.qVuKoL"
subprocess.run(
    ["python3", str(fixture / "run-runtime-fixtures.py"), str(fixture)],
    cwd=project,
    check=True,
)
subprocess.run(
    ["python3", str(update_repo / "10032026-compat/verify-updater-stage.py")],
    cwd=update_repo,
    check=True,
)
print("R3 archive, 19 source mirrors, updater guards/statuses, sequential version resolver, and host fixtures passed.")
