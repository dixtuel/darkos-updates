#!/bin/bash
set -euo pipefail

ZIP_PATH="${1:?update ZIP required}"
ROM_ROOT="${2:?active ROM root required}"
BACKUP_BASE="${3:?rollback directory required}"
EXPECTED_SHA256="${4:?expected ZIP checksum required}"
VERSION="10032026-r2"

if [[ "$EUID" -ne 0 ]]; then echo "Run this installer as root." >&2; exit 1; fi
if [[ "$ROM_ROOT" != roms && "$ROM_ROOT" != roms2 ]] || ! mountpoint -q "/$ROM_ROOT"; then
	echo "The selected ROM card is not mounted." >&2; exit 1
fi
if [[ ! -f "$ZIP_PATH" || ! -r "$ZIP_PATH" || ! "$EXPECTED_SHA256" =~ ^[[:xdigit:]]{64}$ ]]; then
	echo "The update ZIP or expected checksum is invalid." >&2; exit 1
fi
EXPECTED_BACKUP_BASE="/$ROM_ROOT/backup/darkosre-update/$VERSION"
if [[ "$BACKUP_BASE" != "$EXPECTED_BACKUP_BASE" ]] || \
	[[ -L "/$ROM_ROOT/backup" || -L "/$ROM_ROOT/backup/darkosre-update" || -L "$EXPECTED_BACKUP_BASE" ]]; then
	echo "The rollback directory is not the versioned backup path on the selected ROM card." >&2; exit 1
fi
BASE_VERSION="$(cat /home/ark/.config/.VERSION 2>/dev/null)"
if [[ "$BASE_VERSION" != 10032026 && "$BASE_VERSION" != 10032026-r1 ]]; then
	echo "This package requires base OTA 10032026 or 10032026-r1." >&2; exit 1
fi

PATHS_BEFORE="$(grep -o '<path>[^<]*</path>' /etc/emulationstation/es_systems.cfg)"
SWITCH_BEFORE="$(sha256sum '/usr/local/bin/Switch to SD2 for Roms.sh' '/usr/local/bin/Switch to Main SD for Roms.sh')"
if [[ -z "$PATHS_BEFORE" ]] || ! grep -Fq "<path>/$ROM_ROOT/nds" /etc/emulationstation/es_systems.cfg; then
	echo "The NDS system is not using the selected ROM card." >&2; exit 1
fi
echo "$EXPECTED_SHA256  $ZIP_PATH" | sha256sum -c -
unzip -t "$ZIP_PATH" >/dev/null
python3 - "$ZIP_PATH" <<'PY'
import pathlib, stat, sys, zipfile

archive = zipfile.ZipFile(sys.argv[1])
names = set()
symlinks = set()
allowed_exact = {
    "etc/systemd/system/multi-user.target.wants/r36-disable-mali-opencl-aliases.service",
    "etc/systemd/system/r36-disable-mali-opencl-aliases.service",
    "install-r2.sh",
    "opt/DSperate/LICENSE",
    "opt/DSperate/README-upstream-v3.0.0.md",
    "opt/DSperate/config/dsperate.ini",
    "opt/DSperate/dsperate",
    "usr/local/bin/drastic.sh",
    "usr/local/bin/r36_disable_mali_opencl_aliases.sh",
}
abi_dirs = {
    "usr/lib/aarch64-linux-gnu": (2, 183, "AArch64"),
    "usr/lib/arm-linux-gnueabihf": (1, 40, "ARM"),
}
for info in archive.infolist():
    name = info.filename
    if (not name or name.startswith("/") or "\\" in name or
            any(part in ("", ".", "..") for part in name.rstrip("/").split("/"))):
        raise SystemExit(f"unsafe ZIP path: {name!r}")
    normalized = name.rstrip("/")
    if normalized in names:
        raise SystemExit(f"duplicate ZIP path: {name!r}")
    names.add(normalized)
    path = pathlib.PurePosixPath(normalized)
    abi = abi_dirs.get(path.parent.as_posix())
    allowed_library = abi is not None and path.name.startswith("lib") and ".so" in path.name
    if normalized not in allowed_exact and not allowed_library:
        raise SystemExit(f"unexpected payload path: {name!r}")
    mode = info.external_attr >> 16
    kind = stat.S_IFMT(mode)
    if kind == stat.S_IFLNK:
        symlinks.add(normalized)
        target = archive.read(info).decode("utf-8")
        if not target or "\\" in target or any(part == ".." for part in target.split("/")):
            raise SystemExit(f"unsafe symlink target for {name!r}")
        if target.startswith("/"):
            if (normalized != "etc/systemd/system/multi-user.target.wants/"
                    "r36-disable-mali-opencl-aliases.service" or
                    target != "/etc/systemd/system/r36-disable-mali-opencl-aliases.service"):
                raise SystemExit(f"unexpected absolute symlink: {name!r} -> {target!r}")
            continue
        resolved = pathlib.PurePosixPath(normalized).parent.joinpath(target)
        parts = []
        for part in resolved.parts:
            if part == "..":
                if not parts:
                    raise SystemExit(f"symlink escapes root: {name!r} -> {target!r}")
                parts.pop()
            elif part not in ("", "."):
                parts.append(part)
    elif kind not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise SystemExit(f"unsupported ZIP object type: {name!r}")
    if normalized == "opt/DSperate/dsperate" or allowed_library:
        if kind == stat.S_IFLNK:
            continue
        if kind != stat.S_IFREG:
            raise SystemExit(f"ELF payload is not a regular file: {name!r}")
        expected_class, expected_machine, architecture = (2, 183, "AArch64") if normalized == "opt/DSperate/dsperate" else abi
        with archive.open(info) as stream:
            header = stream.read(20)
        if (len(header) < 20 or header[:4] != b"\x7fELF" or header[4] != expected_class or
                header[5] != 1 or int.from_bytes(header[18:20], "little") != expected_machine):
            raise SystemExit(f"ELF class/machine mismatch for {name!r}; expected {architecture}")
for name in names:
    parts = pathlib.PurePosixPath(name).parts
    if any("/".join(parts[:idx]) in symlinks for idx in range(1, len(parts))):
        raise SystemExit(f"ZIP entry is nested beneath a symlink: {name!r}")
PY
AVAILABLE_TMP_KB="$(df -Pk /tmp | awk 'NR == 2 {print $4}')"
if [[ "${AVAILABLE_TMP_KB:-0}" -lt 200000 ]]; then echo "Not enough temporary storage." >&2; exit 1; fi

STAGE="$(mktemp -d /tmp/darkosre-r2.XXXXXX)"
trap 'rm -rf -- "$STAGE"' EXIT
unzip -q "$ZIP_PATH" -d "$STAGE"
while IFS= read -r -d '' candidate; do
	case "$candidate" in
		*/lib*.so*|*/dsperate)
			magic="$(od -An -tx1 -N4 "$candidate" | tr -d ' \n')"
			if [[ ! -s "$candidate" || "$magic" != 7f454c46 ]]; then
				echo "Invalid or empty ELF payload: ${candidate#"$STAGE"/}" >&2; exit 1
			fi
			;;
	esac
done < <(find "$STAGE" -type f -print0)
PAYLOAD_PATHS=()
while IFS= read -r path; do
	[[ -n "$path" && "$path" != install-r2.sh ]] && PAYLOAD_PATHS+=("$path")
done < <(unzip -Z1 "$ZIP_PATH")
UPDATE_PATHS=("etc/emulationstation/es_systems.cfg" "usr/bin/emulationstation/emulationstation.sh" "usr/lib/aarch64-linux-gnu/libOpenCL.so" "usr/lib/arm-linux-gnueabihf/libOpenCL.so")
UPDATE_PATHS+=("${PAYLOAD_PATHS[@]}")

mkdir -p "$BACKUP_BASE"
touch "$BACKUP_BASE/.write-test"
rm -f "$BACKUP_BASE/.write-test"
BACKUP_ARCHIVE="$BACKUP_BASE/rollback.tar"
if [[ ! -f "$BACKUP_BASE/backup-ready" ]]; then
	rm -rf -- "$BACKUP_BASE"
	mkdir -p "$BACKUP_BASE"
	printf '%s\n' "${UPDATE_PATHS[@]}" > "$BACKUP_BASE/managed-paths.txt"
	: > "$BACKUP_BASE/existed-paths.txt"
	EXISTED_PATHS=()
	for path in "${UPDATE_PATHS[@]}"; do
		if [[ -e "/$path" || -L "/$path" ]]; then
			EXISTED_PATHS+=("$path")
			printf '%s\n' "$path" >> "$BACKUP_BASE/existed-paths.txt"
		fi
	done
	if ((${#EXISTED_PATHS[@]})); then
		tar --numeric-owner -cpf "$BACKUP_ARCHIVE.tmp" -C / -- "${EXISTED_PATHS[@]}"
	else
		tar -cpf "$BACKUP_ARCHIVE.tmp" --files-from=/dev/null
	fi
	tar -tf "$BACKUP_ARCHIVE.tmp" >/dev/null
	mv "$BACKUP_ARCHIVE.tmp" "$BACKUP_ARCHIVE"
	sha256sum "$BACKUP_ARCHIVE" > "$BACKUP_BASE/rollback.sha256"
	touch "$BACKUP_BASE/backup-ready"
else
	cmp -s <(printf '%s\n' "${UPDATE_PATHS[@]}") "$BACKUP_BASE/managed-paths.txt"
	sha256sum -c "$BACKUP_BASE/rollback.sha256"
	tar -tf "$BACKUP_ARCHIVE" >/dev/null
fi

rollback() {
	echo "Installation failed; restoring saved files from $BACKUP_BASE." >&2
	for path in "${UPDATE_PATHS[@]}"; do rm -rf -- "/$path"; done
	tar --numeric-owner -xpf "$BACKUP_ARCHIVE" -C /
	systemctl daemon-reload || true
}
for path in "${PAYLOAD_PATHS[@]}"; do
	mkdir -p "/$(dirname "$path")" || { rollback; exit 1; }
	rm -rf -- "/$path" || { rollback; exit 1; }
	cp -a "$STAGE/$path" "/$(dirname "$path")/" || { rollback; exit 1; }
	if [[ ! -L "/$path" ]]; then chown root:root "/$path" || { rollback; exit 1; }; fi
done

if ! python3 - "$ROM_ROOT" <<'PY'
import os, re, stat, sys, tempfile
import xml.etree.ElementTree as ET
path = "/etc/emulationstation/es_systems.cfg"
rom_root = sys.argv[1]
with open(path, "r", encoding="utf-8") as stream:
    content = stream.read()
pattern = re.compile(r"<system>(?:(?!</system>).)*?<name>nds</name>(?:(?!</system>).)*?</system>", re.S)
matches = list(pattern.finditer(content))
if len(matches) != 1:
    raise SystemExit(f"expected one NDS system block, found {len(matches)}")
block = matches[0].group(0)
if not re.search(r"<path>/" + re.escape(rom_root) + r"/nds/?</path>", block):
    raise SystemExit("NDS ROM path does not match selected card")
if "/usr/local/bin/drastic.sh" not in block or "<emulators>" not in block:
    raise SystemExit("NDS launcher block does not match supported R36 layout")
names = re.findall(r'<emulator\s+name="([^"]+)"', block)
if len(names) != len(set(names)):
    raise SystemExit("duplicate NDS emulator entries")
if "dsperate" not in names:
    block = block.replace("</emulators>", '\n                        <emulator name="dsperate">\n                        </emulator>\n                </emulators>', 1)
    content = content[:matches[0].start()] + block + content[matches[0].end():]
ET.fromstring(content)
mode = stat.S_IMODE(os.stat(path).st_mode)
fd, tmp = tempfile.mkstemp(prefix=".es_systems.cfg.", dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)
    os.chmod(tmp, mode)
    os.replace(tmp, path)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
PY
then rollback; exit 1; fi

if ! python3 <<'PY'
import os, shutil, stat, subprocess, tempfile

path = "/usr/bin/emulationstation/emulationstation.sh"
targets = (
    "/opt/system/Advanced/Backup dArkOS Settings.sh",
    "/opt/system/Advanced/Restore dArkOS Settings.sh",
)
pairs = (
    ('"Backup ArkOS Settings"', '"Backup dArkOS Settings"'),
    ('"Restore ArkOS Settings"', '"Restore dArkOS Settings"'),
    ('/opt/system/Advanced/"Backup ArkOS Settings.sh"',
     '/opt/system/Advanced/"Backup dArkOS Settings.sh"'),
    ('/opt/system/Advanced/"Restore ArkOS Settings.sh"',
     '/opt/system/Advanced/"Restore dArkOS Settings.sh"'),
)
if os.path.islink(path) or not os.path.isfile(path) or not os.access(path, os.X_OK):
    raise SystemExit("EmulationStation BaRT wrapper is missing, linked, or not executable")
if any(not os.path.isfile(target) or not os.access(target, os.X_OK) for target in targets):
    raise SystemExit("Expected dArkOS settings handlers are missing or not executable")
with open(path, "r", encoding="utf-8") as stream:
    content = stream.read()
for old, new in pairs:
    old_count, new_count = content.count(old), content.count(new)
    if (old_count, new_count) not in ((1, 0), (0, 1)):
        raise SystemExit(f"BaRT wrapper has unsupported occurrence counts for {old!r}: {old_count}/{new_count}")
    if old_count:
        content = content.replace(old, new, 1)
owner = os.stat(path)
fd, tmp = tempfile.mkstemp(prefix=".emulationstation.sh.", dir=os.path.dirname(path))
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)
    os.chown(tmp, owner.st_uid, owner.st_gid)
    os.chmod(tmp, stat.S_IMODE(owner.st_mode))
    subprocess.run(["bash", "-n", tmp], check=True)
    os.replace(tmp, path)
finally:
    if os.path.exists(tmp):
        os.unlink(tmp)
PY
then rollback; exit 1; fi

if ! /usr/local/bin/r36_disable_mali_opencl_aliases.sh; then rollback; exit 1; fi
if ! systemctl daemon-reload || ! systemctl start r36-disable-mali-opencl-aliases.service; then rollback; exit 1; fi
PATHS_AFTER="$(grep -o '<path>[^<]*</path>' /etc/emulationstation/es_systems.cfg)"
SWITCH_AFTER="$(sha256sum '/usr/local/bin/Switch to SD2 for Roms.sh' '/usr/local/bin/Switch to Main SD for Roms.sh')"
if [[ "$PATHS_BEFORE" != "$PATHS_AFTER" || "$SWITCH_BEFORE" != "$SWITCH_AFTER" ]] || \
	[[ "$(grep -c '<emulator name="dsperate">' /etc/emulationstation/es_systems.cfg)" -ne 1 ]]; then
	rollback; exit 1
fi
loader_check() {
	local loader="$1" search_path="$2" binary="$3" output status
	[[ -x "$loader" && -e "$binary" ]] || { echo "Missing loader or ELF file: $binary" >&2; return 1; }
	output="$(LD_LIBRARY_PATH="$search_path" "$loader" --list "$binary" 2>&1)"; status=$?
	if [[ $status -ne 0 || -z "$output" ]] || grep -Eiq 'not found|error while loading|cannot open shared object' <<<"$output"; then
		echo "Loader check failed for $binary:" >&2
		printf '%s\n' "$output" >&2
		return 1
	fi
}

AARCH64_LIBS="/usr/lib/aarch64-linux-gnu:/lib/aarch64-linux-gnu"
ARMHF_LIBS="/usr/lib/arm-linux-gnueabihf:/lib/arm-linux-gnueabihf"
if ! loader_check /lib/ld-linux-aarch64.so.1 "$AARCH64_LIBS" /opt/DSperate/dsperate || \
	! /opt/DSperate/dsperate --version | grep -q 'DSperate v3.0.0'; then
	rollback; exit 1
fi
ES_BINARY="/usr/bin/emulationstation/emulationstation"
if ! loader_check /lib/ld-linux-aarch64.so.1 "$AARCH64_LIBS" "$ES_BINARY"; then
	rollback; exit 1
fi
for path in "${PAYLOAD_PATHS[@]}"; do
	case "$path" in
		usr/lib/aarch64-linux-gnu/lib*.so*)
			if ! loader_check /lib/ld-linux-aarch64.so.1 "$AARCH64_LIBS" "/$path"; then rollback; exit 1; fi
			;;
		usr/lib/arm-linux-gnueabihf/lib*.so*)
			if ! loader_check /lib/ld-linux-armhf.so.3 "$ARMHF_LIBS" "/$path"; then rollback; exit 1; fi
			;;
	esac
done

touch "/home/ark/.config/.update10032026-r2"
echo "10032026-r2" > /home/ark/.config/.VERSION
sed -i "/title=/c\\title=dArkOSRE (10032026-r2)" /usr/share/plymouth/themes/text.plymouth
echo "Installed DSperate v3.0.0 and PortMaster legacy libraries. ROM paths remain on /$ROM_ROOT; rollback is at $BACKUP_BASE."
systemctl reboot
