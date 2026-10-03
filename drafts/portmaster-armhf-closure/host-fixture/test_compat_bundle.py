"""Host-only archive tests for the dated compat payload wrapper."""

import hashlib
import importlib.util
import stat
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WRAPPER = ROOT / "10032026-compat" / "apply_portmaster_compat.py"
ARCHIVE = ROOT / "10032026-compat" / "darkosupdate10032026-compat.zip"
SPEC = importlib.util.spec_from_file_location("compat_wrapper", WRAPPER)
wrapper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wrapper)


def assert_refused(callback, message):
    try:
        callback()
    except wrapper.Refused:
        return
    raise AssertionError(message)


def test_archive():
    manifest, infos = wrapper.inspect_bundle(ARCHIVE)
    assert len(manifest["new_armhf_packages"]) == 26
    assert len(infos) == 57
    assert wrapper.EXPECTED_ARCHIVE_SHA256 == wrapper.sha256_file(ARCHIVE)
    assert_refused(lambda: wrapper.inspect_bundle(ARCHIVE, "0" * 64),
                   "accepted a bundle with the wrong pinned SHA-256")

    for unsafe in ("../escape", "/absolute", "dir\\escape", "a/../b"):
        assert_refused(lambda unsafe=unsafe: wrapper.safe_member_name(unsafe),
                       f"accepted unsafe member path {unsafe!r}")

    assert wrapper.configured_rom_root(["/roms2/nds", "/roms2/ports"], {"/roms", "/roms2"}) == "/roms2"
    assert wrapper.configured_rom_root(["/roms/nes"], {"/roms", "/roms2"}) == "/roms"
    for paths, mounted in ((["/roms/nes", "/roms2/ports"], {"/roms", "/roms2"}),
                           (["/roms2/ports"], {"/roms"}),
                           (["/other/roms"], {"/roms", "/roms2"})):
        assert_refused(lambda paths=paths, mounted=mounted:
                       wrapper.configured_rom_root(paths, mounted),
                       "accepted ambiguous/unmounted active ROM card")

    with tempfile.TemporaryDirectory(prefix="compat-bundle-fixture-") as tmp:
        duplicate = Path(tmp) / "duplicate.zip"
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr("duplicate", b"one")
            archive.writestr("duplicate", b"two")
        duplicate_hash = wrapper.sha256_file(duplicate)
        assert_refused(lambda: wrapper.inspect_bundle(duplicate, duplicate_hash),
                       "accepted duplicate ZIP members")

        symlink = Path(tmp) / "symlink.zip"
        info = zipfile.ZipInfo("fake")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(symlink, "w") as archive:
            archive.writestr(info, b"../../etc/passwd")
        symlink_hash = wrapper.sha256_file(symlink)
        assert_refused(lambda: wrapper.inspect_bundle(symlink, symlink_hash),
                       "accepted a symlink ZIP member")


if __name__ == "__main__":
    test_archive()
    print("PASS compat archive fixtures: exact bundle, checksum, traversal, duplicate and symlink refusal")
