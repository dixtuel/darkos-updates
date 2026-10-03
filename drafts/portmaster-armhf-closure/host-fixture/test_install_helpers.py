"""Small helper fixtures; no dpkg/apt invocation or device writes."""

import importlib.util
import json
import tempfile
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("installer", BASE / "install_armhf_closure.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
FIXTURES = json.loads((Path(__file__).parent / "fixtures.json").read_text())


def main():
    assert "/sbin" in installer.SYSTEM_PATH.split(":")
    assert "/usr/sbin" in installer.SYSTEM_PATH.split(":")
    assert installer.command_environment()["PATH"] == installer.SYSTEM_PATH
    expected_missing = sorted(installer.REQUIRED_TOOLS - {"dpkg"})
    assert installer.missing_required_tools({"dpkg"}) == expected_missing
    assert {"ldconfig", "start-stop-daemon"} <= set(expected_missing)
    assert installer.configured_rom_root(["/roms2/nds", "/roms2/ports"], {"/roms", "/roms2"}) == "/roms2"
    assert installer.configured_rom_root(["/roms/nes"], {"/roms", "/roms2"}) == "/roms"
    for paths, mounted in ((["/roms/nes", "/roms2/ports"], {"/roms", "/roms2"}),
                           (["/roms2/ports"], {"/roms"}),
                           (["/other/roms"], {"/roms", "/roms2"})):
        try:
            installer.configured_rom_root(paths, mounted)
        except installer.GateError:
            pass
        else:
            raise AssertionError(f"accepted ambiguous/unmounted ES ROM paths: {paths} {mounted}")

    helpers = FIXTURES["installer_helpers"]
    manifest = FIXTURES["manifest_subset"]["new_armhf_packages"]
    records = installer.parse_status_text(helpers["partial_resume_status"])
    candidates = {p["Package"]: p["Version"] for p in manifest}
    before = {("kept", "arm64"): {"Version": "1", "Status": "install ok installed"}}
    after = {**before, (helpers["partial_resume_expected_candidate"], "armhf"):
             {"Version": candidates[helpers["partial_resume_expected_candidate"]], "Status": "install ok installed"}}
    assert installer.unrelated_status_changes(before, after, candidates) == []
    changed_unrelated = {("kept", "arm64"): {"Version": "2", "Status": "install ok installed"}}
    assert installer.unrelated_status_changes(before, changed_unrelated, candidates) == [("kept", "arm64")]
    resume = installer.classify_packages(records, candidates, resume=True)
    assert helpers["partial_resume_expected_candidate"] in resume
    try:
        installer.classify_packages(records, candidates, resume=False)
    except installer.GateError:
        pass
    else:
        raise AssertionError("normal mode accepted a partial package")

    for line, expected in zip(helpers["shared_owner_lines"], helpers["shared_owner_arch_sets"]):
        path = line.rsplit(": ", 1)[1]
        assert installer.parse_dpkg_owners(line + "\n", "libvdpau1") == set(expected), path
    for line in helpers["reject_owner_lines"]:
        try:
            installer.parse_dpkg_owners(line + "\n", "libvdpau1")
        except installer.GateError:
            pass
        else:
            raise AssertionError(f"accepted unsafe dpkg owner: {line}")

    try:
        installer.check_relations(helpers["unsupported_relation"], {}, {}, "fixture", "Depends")
    except installer.GateError:
        pass
    else:
        raise AssertionError("accepted unsupported :any relation")

    installer.check_replaces("libnorm1", {}, "libnorm1t64")
    replaced_package = {("libnorm1", "arm64"): {
        "Package": "libnorm1", "Architecture": "arm64", "Version": "1.5.8-1",
        "Status": "install ok installed",
    }}
    try:
        installer.check_replaces("libnorm1", replaced_package, "libnorm1t64")
    except installer.GateError:
        pass
    else:
        raise AssertionError("accepted takeover of an installed Replaces target")

    with tempfile.TemporaryDirectory(prefix="pm-closure-ancestor-") as tmp:
        root = Path(tmp)
        (root / "link").symlink_to("/usr/lib", target_is_directory=True)
        try:
            installer.check_existing_ancestors(root / "link" / "future" / "libx.so")
        except installer.GateError:
            pass
        else:
            raise AssertionError("accepted unreviewed symlink ancestor")
    print("PASS installer helper fixtures: system PATH/tool gate, ES-selected ROM backup, partial resume, multi-owner parsing, fail-closed relation/ownership and ancestor")


if __name__ == "__main__":
    main()
