#!/usr/bin/env python3
"""Exercise the updater's exact ROM-root resolver in isolated fixtures."""

import hashlib
import pathlib
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
UPDATER = ROOT / "dArkOSUpdate.sh"
text = UPDATER.read_text()
start = text.index("# BEGIN ROM_ROOT_RESOLVER\n") + len("# BEGIN ROM_ROOT_RESOLVER\n")
end = text.index("# END ROM_ROOT_RESOLVER\n", start)
resolver = text[start:end]

for stage in ("10032026", "10032026-r1", "10032026-r2"):
    if f'BACKUP_BASE="$ROM_BACKUP_ROOT/{stage}"' not in text and \
            f'BACKUP_BASE="$ROM_BACKUP_ROOT/$PATCH_VERSION"' not in text:
        raise AssertionError(f"{stage}: rollback path does not use the shared ROM root")
if "HAS_ROM2_PATH=" in text:
    raise AssertionError("duplicate R3/R4 ROM-root selection remains in the updater")
if 'ROM_BACKUP_ROOT="/$ROM_ROOT/backup/darkosre-update"' not in text:
    raise AssertionError("the shared ROM selection is not connected to the rollback root")


def digest_tree(root):
    result = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            result.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
        elif path.is_dir():
            result.append((relative, "directory"))
    return result


def run_case(name, paths, mounted, expected_root):
    with tempfile.TemporaryDirectory(prefix="rom-root-resolver-") as temp:
        root = pathlib.Path(temp)
        mount_root = root / "mounts"
        mount_root.mkdir()
        for card in mounted:
            card_dir = mount_root / card
            card_dir.mkdir()
            (card_dir / ".mounted-fixture").write_text("mounted\n")

        es_config = root / "es_systems.cfg"
        es_config.write_text("\n".join(f"<path>{path}</path>" for path in paths) + "\n")
        mock_bin = root / "bin"
        mock_bin.mkdir()
        mountpoint = mock_bin / "mountpoint"
        mountpoint.write_text(
            "#!/bin/bash\n"
            "[[ \"$1\" == -q && -f \"$2/.mounted-fixture\" ]]\n"
        )
        mountpoint.chmod(0o755)

        runner = root / "runner.sh"
        runner.write_text(
            "#!/bin/bash\n"
            "set -u\n"
            + resolver
            + "\n"
            + 'ROM_ROOT="$(resolve_rom_root "$1" "$2")" || exit $?\n'
            + 'printf "root=%s\\nbackup=/%s/backup/darkosre-update/10032026-r1\\n" "$ROM_ROOT" "$ROM_ROOT"\n'
        )
        runner.chmod(0o755)

        before = digest_tree(root)
        result = subprocess.run(
            ["bash", str(runner), str(es_config), str(mount_root)],
            env={"PATH": f"{mock_bin}:/usr/bin:/bin"},
            capture_output=True,
            text=True,
        )
        after = digest_tree(root)
        if before != after:
            raise AssertionError(f"{name}: resolver modified fixture files")

        if expected_root is None:
            if result.returncode == 0:
                raise AssertionError(f"{name}: expected fail-closed refusal, got {result.stdout!r}")
            if "backup=" in result.stdout:
                raise AssertionError(f"{name}: refusal selected a backup destination")
        else:
            expected = (
                f"root={expected_root}\n"
                f"backup=/{expected_root}/backup/darkosre-update/10032026-r1\n"
            )
            if result.returncode != 0 or result.stdout != expected:
                raise AssertionError(
                    f"{name}: expected {expected!r}, got rc={result.returncode}, "
                    f"stdout={result.stdout!r}, stderr={result.stderr!r}"
                )


run_case("both mounted, ES selects /roms", ["/roms/nes", "/roms/psp"], {"roms", "roms2"}, "roms")
run_case("both mounted, ES selects /roms2", ["/roms2/nes", "/roms2/psp"], {"roms", "roms2"}, "roms2")
run_case("only /roms mounted", ["/roms/nes"], {"roms"}, "roms")
run_case("SD2 absent, ES selects /roms", ["/roms/nes", "/opt/cmds/"], {"roms"}, "roms")
run_case("ES selects unmounted /roms2", ["/roms2/nes"], {"roms"}, None)
run_case("mixed ROM roots", ["/roms/nes", "/roms2/psp"], {"roms", "roms2"}, None)
run_case("no ROM paths", ["/opt/cmds/", "/usr/local/bin/kodi/"], {"roms", "roms2"}, None)
print("ROM-root resolver fixtures passed: selection, backup routing, and no-write refusal checks.")
