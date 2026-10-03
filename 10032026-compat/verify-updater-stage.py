#!/usr/bin/env python3
"""Exercise the raw compatibility updater stage against temporary fixtures."""
import hashlib
import os
import pathlib
import re
import subprocess
import tempfile
import zipfile


stage = pathlib.Path(__file__).resolve().parent
repo = stage.parent
project = stage.parents[2]
updater = (repo / "dArkOSUpdate.sh").read_text()
start = updater.index('COMPAT_VERSION="10032026-compat"')
end = updater.index('PATCH_VERSION="10032026-r2"', start)
compat_source = updater[start:end]
zip_path = stage / "darkosupdate10032026-compat.zip"
wrapper_path = stage / "apply_portmaster_compat.py"
zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
wrapper_sha = hashlib.sha256(wrapper_path.read_bytes()).hexdigest()

zip_match = re.search(r'COMPAT_ZIP_SHA256="([0-9a-f]{64})"', compat_source)
wrapper_match = re.search(r'COMPAT_WRAPPER_SHA256="([0-9a-f]{64})"', compat_source)
assert zip_match and zip_match.group(1) == zip_sha, "updater ZIP SHA does not match staged bundle"
assert wrapper_match and wrapper_match.group(1) == wrapper_sha, "updater wrapper SHA does not match staged wrapper"
with zipfile.ZipFile(zip_path) as archive:
    assert archive.testzip() is None

verified = subprocess.run(
    ["python3", str(wrapper_path), str(zip_path), "--verify-only"],
    cwd=repo,
    text=True,
    capture_output=True,
)
assert verified.returncode == 0, (verified.stdout, verified.stderr)

with tempfile.TemporaryDirectory(prefix="compat-updater-flow-") as temporary:
    root = pathlib.Path(temporary)
    config = root / "home/ark/.config"
    config.mkdir(parents=True)
    mock_bin = root / "bin"
    mock_bin.mkdir()
    temp_root = root / "tmp"
    temp_root.mkdir()
    fake_loaders = root / "loaders"
    fake_loaders.mkdir()
    call_log = root / "loader-calls.txt"
    wrapper_log = root / "wrapper-calls.txt"

    wget = mock_bin / "wget"
    wget.write_text(r'''#!/bin/bash
set -euo pipefail
output=""; url=""
while (($#)); do
  case "$1" in
    -O) output="$2"; shift 2 ;;
    -a|-t|-T) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
case "$url" in
  */darkosupdate10032026-compat.zip) source="$COMPAT_FIXTURE_DIR/darkosupdate10032026-compat.zip"; kind=zip ;;
  */apply_portmaster_compat.py) source="$COMPAT_FIXTURE_DIR/apply_portmaster_compat.py"; kind=wrapper ;;
  *) exit 90 ;;
esac
if [[ "${FAIL_DOWNLOAD:-}" == "$kind" ]]; then exit 9; fi
cp "$source" "$output"
if [[ "${CORRUPT_DOWNLOAD:-}" == "$kind" ]]; then printf x >> "$output"; fi
''')
    wget.chmod(0o755)

    loader_script = mock_bin / "mock-loader"
    loader_script.write_text(r'''#!/bin/bash
set -euo pipefail
printf '%s\n' "$0 $*" >> "$LOADER_CALL_LOG"
count="$(wc -l < "$LOADER_CALL_LOG")"
[[ "${FAIL_LOADER_AT:-0}" != "$count" ]]
''')
    loader_script.chmod(0o755)
    armhf_loader = fake_loaders / "ld-linux-armhf.so.3"
    aarch64_loader = fake_loaders / "ld-linux-aarch64.so.1"
    armhf_loader.symlink_to(loader_script)
    aarch64_loader.symlink_to(loader_script)

    compat_source = compat_source.replace(
        'mktemp -d /tmp/darkos-compat.XXXXXX',
        f'mktemp -d {temp_root}/darkos-compat.XXXXXX',
    )
    compat_source = compat_source.replace('/home/ark/.config', str(config))
    compat_source = compat_source.replace('/lib/ld-linux-armhf.so.3', str(armhf_loader))
    compat_source = compat_source.replace('/lib/ld-linux-aarch64.so.1', str(aarch64_loader))

    def run_case(name, version, *, fail_download="", corrupt_download="", wrapper_status=0,
                 fail_loader_at=0, terminal_after_success=False):
        for child in config.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                import shutil
                shutil.rmtree(child)
        (config / ".VERSION").write_text(version + "\n")
        if version in ("10032026-r2", "10032026-r3"):
            (config / ".update10032026-r2").touch()
        if version == "10032026-r3":
            (config / ".update10032026-r3").touch()
        call_log.unlink(missing_ok=True)
        wrapper_log.unlink(missing_ok=True)
        test_script = root / f"{name}.sh"
        tail = 'printf "compat-stage-returned\\n"\nexit 0\n'
        if terminal_after_success:
            tail = f'''if [[ ! -f "{config}/.update10032026-r2" ]]; then echo R2_ELIGIBLE; exit 91; fi
if [[ ! -f "{config}/.update10032026-r3" ]]; then echo R3_ELIGIBLE; exit 92; fi
exit 187
'''
        prelude = f'''#!/bin/bash
set +e
LOCATION="https://raw.example.invalid/feed"
LOG_FILE="{root}/update.log"
COMPAT_UPDATE_DONE="{config}/.update10032026-compat"
COMPAT_FIXTURE_DIR="{stage}"
LOADER_CALL_LOG="{call_log}"
WRAPPER_CALL_LOG="{wrapper_log}"
MOCK_WRAPPER_STATUS="{wrapper_status}"
FAIL_DOWNLOAD="{fail_download}"
CORRUPT_DOWNLOAD="{corrupt_download}"
FAIL_LOADER_AT="{fail_loader_at}"
PATH="{mock_bin}:$PATH"
export COMPAT_FIXTURE_DIR LOADER_CALL_LOG FAIL_DOWNLOAD CORRUPT_DOWNLOAD FAIL_LOADER_AT PATH
sudo() {{
  printf '%s\\n' "$*" >> "$WRAPPER_CALL_LOG"
  return "$MOCK_WRAPPER_STATUS"
}}
'''
        test_script.write_text(prelude + compat_source + tail)
        proc = subprocess.run(["bash", str(test_script)], text=True, capture_output=True)
        marker = config / ".update10032026-compat"
        loaders = call_log.read_text().splitlines() if call_log.exists() else []
        invocations = wrapper_log.read_text().splitlines() if wrapper_log.exists() else []
        version_after = (config / ".VERSION").read_text().strip()
        assert version_after == version, (name, version_after)
        return proc, marker.exists(), loaders, invocations

    # Either download failing, or either downloaded artifact failing its hash,
    # must stop before invoking the package wrapper or setting a marker.
    p, marker, loaders, calls = run_case("download-zip-failure", "10032026", fail_download="zip")
    assert p.returncode == 1 and not marker and not calls and not loaders
    p, marker, loaders, calls = run_case("download-wrapper-failure", "10032026", fail_download="wrapper")
    assert p.returncode == 1 and not marker and not calls and not loaders
    p, marker, loaders, calls = run_case("hash-zip-failure", "10032026-r1", corrupt_download="zip")
    assert p.returncode == 1 and not marker and not calls and not loaders
    p, marker, loaders, calls = run_case("hash-wrapper-failure", "10032026-r1", corrupt_download="wrapper")
    assert p.returncode == 1 and not marker and not calls and not loaders

    # Installer failures pass through. On base/R1 success, only the compat
    # marker is set; .VERSION remains unchanged and R2 is eligible next.
    p, marker, loaders, calls = run_case("wrapper-failure", "10032026-r1", wrapper_status=23)
    assert p.returncode == 23 and not marker and not loaders and len(calls) == 1, (p.returncode, p.stdout, p.stderr, marker, loaders, calls)
    for version in ("10032026", "10032026-r1"):
        p, marker, loaders, calls = run_case("base-or-r1-success", version)
        assert p.returncode == 0 and marker and not loaders and len(calls) == 1

    # R2/R3 states run exactly five checks per ABI before recording the marker.
    for version in ("10032026-r2", "10032026-r3"):
        p, marker, loaders, calls = run_case("newer-version-success", version)
        assert p.returncode == 0 and marker and len(loaders) == 10 and len(calls) == 1
        assert sum("ld-linux-armhf" in line for line in loaders) == 5
        assert sum("ld-linux-aarch64" in line for line in loaders) == 5

    # Any failed loader check leaves the marker unset and the version intact.
    p, marker, loaders, calls = run_case("loader-failure", "10032026-r2", fail_loader_at=6)
    assert p.returncode == 1 and not marker and len(loaders) == 6 and len(calls) == 1

    # On an already-installed R3, successful compatibility work returns the
    # updater terminal status and does not make R3 eligible again.
    p, marker, loaders, calls = run_case(
        "r3-compat-terminal", "10032026-r3", terminal_after_success=True
    )
    assert p.returncode == 187 and marker and len(loaders) == 10, (p.returncode, p.stdout, p.stderr, marker, loaders, calls)
    assert "R3_ELIGIBLE" not in p.stdout and "R2_ELIGIBLE" not in p.stdout

print("Compatibility updater fixture passed: download/hash guards, preserved wrapper failure, version/marker policy, ten ABI loader checks, loader-failure refusal, and R3 terminal flow.")
