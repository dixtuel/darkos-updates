#!/bin/bash
set -Eeuo pipefail

ZIP_PATH="${1:?Usage: install-runtime.sh OTA.zip OTA_SHA256}"
EXPECTED_ZIP_SHA256="${2:?Usage: install-runtime.sh OTA.zip OTA_SHA256}"
VERSION="10032026-r3"
BASE_VERSION="10032026-r2"
ZRAM_BASE_SHA256="237d0729fbc1c8ee2a7dfd50740e304e020a8d1d33e21bd2d65e5b2ef3a724d3"
ZRAM_TARGET_SHA256="6429ec1445eb16e865c633112579fa90ca7c634fff0cc4cb5e08ed481be7af3e"
WIFI_SERVICE_SHA256="726e2b2356278fd46035091772f28703ee9e5d6f2bf04bbff7e3ec9d512387fd"
WIFI_LINK_TARGET="/etc/systemd/system/wifi_importer.service"
PPSSPP_DB_BASE_SHA256="45ce6ad8b8f932ac1cffebd5bb0b23a67ff4813bf9169ec72ba20aef7b278e5d"
PPSSPP_DB_TARGET_SHA256="741a2b21cc85c12c58f1edbe325d610b09fb81d872b9fb3fbb84c4abf86159c5"

# This environment override exists only for disposable host fixtures. Normal
# device runs always operate on / and require root.
if [[ -n "${R36_TEST_ROOT:-}" ]]; then
	ROOT_DIR="$(realpath -e -- "$R36_TEST_ROOT")"
	[[ "$ROOT_DIR" != / ]] || { echo "Test root cannot be /." >&2; exit 1; }
	TEST_MODE=1
else
	[[ "$EUID" -eq 0 ]] || { echo "Run this installer as root." >&2; exit 1; }
	ROOT_DIR="/"
	TEST_MODE=0
fi

root_path() {
	if [[ "$ROOT_DIR" == / ]]; then printf '/%s' "$1"; else printf '%s/%s' "$ROOT_DIR" "$1"; fi
}

declare -A EXPECTED_SHA EXPECTED_MODE EXPECTED_KIND EXPECTED_TARGET
PAYLOAD_PATHS=(
	"usr/local/bin/ppsspp.sh"
	"usr/local/bin/importwifi.sh"
	"usr/local/bin/zram-autostart.sh"
	"opt/system/Advanced/Restore Default PPSSPP Controls.sh"
	"opt/system/ZRam Manager.sh"
	"etc/systemd/system/wifi_importer.service"
	"etc/systemd/system/multi-user.target.wants/wifi_importer.service"
	"etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf"
	"etc/systemd/system/zram-swap.service"
	"opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini"
	"opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini"
	"opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl"
	"opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini"
	"opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini"
	"opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl"
	"usr/local/bin/bigpemu.sh"
	"usr/local/bin/perfmax"
	"usr/local/bin/perfnorm"
	"opt/ppsspp/assets/gamecontrollerdb.txt"
)

EXPECTED_SHA[usr/local/bin/ppsspp.sh]=9cc6ab8a1c82154950d52f61f3a223cfc5b66d8b9ec373ea1b2e3637ab5d89e8
EXPECTED_MODE[usr/local/bin/ppsspp.sh]=755
EXPECTED_KIND[usr/local/bin/ppsspp.sh]=file
EXPECTED_SHA[usr/local/bin/importwifi.sh]=e2dfeee2ac467a9f1385f87351e6af7ce2285360d4b6bd040b9113fa72054667
EXPECTED_MODE[usr/local/bin/importwifi.sh]=755
EXPECTED_KIND[usr/local/bin/importwifi.sh]=file
EXPECTED_SHA[usr/local/bin/zram-autostart.sh]=93a21e451328f1dfd99f8338762a877e176de0d7525074fe484b7f07754e8ea8
EXPECTED_MODE[usr/local/bin/zram-autostart.sh]=755
EXPECTED_KIND[usr/local/bin/zram-autostart.sh]=file
EXPECTED_SHA[opt/system/Advanced/Restore Default PPSSPP Controls.sh]=e8aea06956a61256f8efb1cd2db61c5bb60004424cfafd3c651078faa04487d6
EXPECTED_MODE[opt/system/Advanced/Restore Default PPSSPP Controls.sh]=755
EXPECTED_KIND[opt/system/Advanced/Restore Default PPSSPP Controls.sh]=file
EXPECTED_SHA[opt/system/ZRam Manager.sh]=3e10b3d41a80c9b8223f3adda507fd37b3c2bc9c134da5c4fc58defb458b5d18
EXPECTED_MODE[opt/system/ZRam Manager.sh]=755
EXPECTED_KIND[opt/system/ZRam Manager.sh]=file
EXPECTED_SHA[etc/systemd/system/wifi_importer.service]=726e2b2356278fd46035091772f28703ee9e5d6f2bf04bbff7e3ec9d512387fd
EXPECTED_MODE[etc/systemd/system/wifi_importer.service]=644
EXPECTED_KIND[etc/systemd/system/wifi_importer.service]=file
EXPECTED_KIND[etc/systemd/system/multi-user.target.wants/wifi_importer.service]=symlink
EXPECTED_TARGET[etc/systemd/system/multi-user.target.wants/wifi_importer.service]="$WIFI_LINK_TARGET"
EXPECTED_SHA[etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf]=ed4bf4264b6e298454688d84fa253da69f83b7cdc661a46f1de8895a38566bbc
EXPECTED_MODE[etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf]=644
EXPECTED_KIND[etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf]=file
EXPECTED_SHA[etc/systemd/system/zram-swap.service]="$ZRAM_TARGET_SHA256"
EXPECTED_MODE[etc/systemd/system/zram-swap.service]=644
EXPECTED_KIND[etc/systemd/system/zram-swap.service]=file
EXPECTED_SHA[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini]=83dcbc75635a88dba815fc423fc87b2404a70d339e49e442e802af92a481c537
EXPECTED_MODE[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini]=755
EXPECTED_KIND[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini]=file
EXPECTED_SHA[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini]=56da9d455359d6968fe95e9f0be3c3628772a002999b76eb8f10c398d317e490
EXPECTED_MODE[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini]=755
EXPECTED_KIND[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini]=file
EXPECTED_SHA[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl]=56da9d455359d6968fe95e9f0be3c3628772a002999b76eb8f10c398d317e490
EXPECTED_MODE[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl]=755
EXPECTED_KIND[opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl]=file
EXPECTED_SHA[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini]=83dcbc75635a88dba815fc423fc87b2404a70d339e49e442e802af92a481c537
EXPECTED_MODE[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini]=755
EXPECTED_KIND[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini]=file
EXPECTED_SHA[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini]=078caec2702eab56a4f657fea8fa6f5954dc29249195a77b4b7b3091744ee777
EXPECTED_MODE[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini]=755
EXPECTED_KIND[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini]=file
EXPECTED_SHA[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl]=078caec2702eab56a4f657fea8fa6f5954dc29249195a77b4b7b3091744ee777
EXPECTED_MODE[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl]=755
EXPECTED_KIND[opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl]=file
EXPECTED_SHA[usr/local/bin/bigpemu.sh]=aa14e7c92c6ec2d5bfe41643054d68a9fce24e225625e7901a4eb5625e471ccc
EXPECTED_MODE[usr/local/bin/bigpemu.sh]=755
EXPECTED_KIND[usr/local/bin/bigpemu.sh]=file
EXPECTED_SHA[usr/local/bin/perfmax]=9a8c45cac25bf76dc0dd8bdda5c2b7c98f08f610481dbaaea6da4cf5fb3d8fab
EXPECTED_MODE[usr/local/bin/perfmax]=755
EXPECTED_KIND[usr/local/bin/perfmax]=file
EXPECTED_SHA[usr/local/bin/perfnorm]=f83e458db52c6f14ab66d62e4d2e4605fda7d2b91dc31b13f0c16fa6e8ab3295
EXPECTED_MODE[usr/local/bin/perfnorm]=755
EXPECTED_KIND[usr/local/bin/perfnorm]=file
EXPECTED_SHA[opt/ppsspp/assets/gamecontrollerdb.txt]="$PPSSPP_DB_TARGET_SHA256"
EXPECTED_MODE[opt/ppsspp/assets/gamecontrollerdb.txt]=644
EXPECTED_KIND[opt/ppsspp/assets/gamecontrollerdb.txt]=file

[[ -f "$ZIP_PATH" && -r "$ZIP_PATH" && "$EXPECTED_ZIP_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || {
	echo "The runtime ZIP or checksum argument is invalid." >&2; exit 1;
}
echo "$EXPECTED_ZIP_SHA256  $ZIP_PATH" | sha256sum -c -

VERSION_FILE="$(root_path home/ark/.config/.VERSION)"
PPSSPP_DB="$(root_path opt/ppsspp/assets/gamecontrollerdb.txt)"
BASE_MARKER="$(root_path home/ark/.config/.update$BASE_VERSION)"
NEW_MARKER="$(root_path "home/ark/.config/.update$VERSION")"
ES_CONFIG="$(root_path etc/emulationstation/es_systems.cfg)"
SWITCH_SD2="$(root_path 'usr/local/bin/Switch to SD2 for Roms.sh')"
SWITCH_MAIN="$(root_path 'usr/local/bin/Switch to Main SD for Roms.sh')"
PLYMOUTH_FILE="$(root_path usr/share/plymouth/themes/text.plymouth)"

if [[ "$TEST_MODE" -eq 1 ]]; then
	ROM2_MOUNT="$(root_path roms2)"
	ROM1_MOUNT="$(root_path roms)"
else
	ROM2_MOUNT="/roms2"
	ROM1_MOUNT="/roms"
fi
ROM_PATHS_BEFORE="$(grep -o '<path>[^<]*</path>' "$ES_CONFIG")"
HAS_ROM2_PATH=0
HAS_ROM1_PATH=0
grep -Fq '<path>/roms2/' "$ES_CONFIG" && HAS_ROM2_PATH=1 || true
grep -Fq '<path>/roms/' "$ES_CONFIG" && HAS_ROM1_PATH=1 || true
if [[ "$HAS_ROM2_PATH" -eq 1 && "$HAS_ROM1_PATH" -eq 0 ]] && mountpoint -q "$ROM2_MOUNT"; then
	ROM_ROOT="roms2"
elif [[ "$HAS_ROM1_PATH" -eq 1 && "$HAS_ROM2_PATH" -eq 0 ]] && mountpoint -q "$ROM1_MOUNT"; then
	ROM_ROOT="roms"
else
	echo "EmulationStation ROM paths and mounted card selection are missing or ambiguous." >&2; exit 1
fi
BACKUP_BASE="$(root_path "$ROM_ROOT/backup/darkosre-update/$VERSION")"

[[ -f "$VERSION_FILE" && ! -L "$VERSION_FILE" && "$(<"$VERSION_FILE")" == "$BASE_VERSION" && -f "$BASE_MARKER" && ! -L "$BASE_MARKER" ]] || {
	echo "This runtime OTA requires matching $BASE_VERSION .VERSION and completion marker." >&2; exit 1;
}
[[ ! -e "$NEW_MARKER" && ! -L "$NEW_MARKER" ]] || {
	echo "The runtime OTA marker already exists; updater state needs review." >&2; exit 1;
}
if [[ -e "$PPSSPP_DB" || -L "$PPSSPP_DB" ]]; then
	[[ -f "$PPSSPP_DB" && ! -L "$PPSSPP_DB" ]] || {
		echo "The PPSSPP controller database is not a regular file; refusing replacement." >&2; exit 1;
	}
	PPSSPP_DB_SHA="$(sha256sum "$PPSSPP_DB" | awk '{print $1}')"
	[[ "$PPSSPP_DB_SHA" == "$PPSSPP_DB_BASE_SHA256" || "$PPSSPP_DB_SHA" == "$PPSSPP_DB_TARGET_SHA256" ]] || {
		echo "The PPSSPP controller database is customized or unrecognized; refusing replacement." >&2; exit 1;
	}
fi
for path in "$ES_CONFIG" "$SWITCH_SD2" "$SWITCH_MAIN" "$PLYMOUTH_FILE"; do
	[[ -f "$path" && ! -L "$path" ]] || { echo "Required R36 configuration file is missing or linked: $path" >&2; exit 1; }
done
ES_CONFIG_SHA_BEFORE="$(sha256sum "$ES_CONFIG" | awk '{print $1}')"
SWITCH_SHA_BEFORE="$(sha256sum "$SWITCH_SD2" "$SWITCH_MAIN")"

ZRAM_UNIT="$(root_path etc/systemd/system/zram-swap.service)"
ZRAM_INSTALL_UNIT=1
ZRAM_UNIT_STATE="regular"
ZRAM_SHA_BEFORE=""
if [[ -L "$ZRAM_UNIT" ]]; then
	if [[ "$(readlink "$ZRAM_UNIT")" == /dev/null ]]; then
		ZRAM_INSTALL_UNIT=0
		ZRAM_UNIT_STATE="masked"
	else
		echo "The zram unit is a custom symlink; refusing to replace it." >&2; exit 1
	fi
elif [[ ! -e "$ZRAM_UNIT" ]]; then
	# An absent unit may represent an explicit user opt-out. Leave it absent;
	# the rest of this runtime OTA remains independently useful.
	ZRAM_INSTALL_UNIT=0
	ZRAM_UNIT_STATE="absent"
elif [[ -f "$ZRAM_UNIT" ]]; then
	ZRAM_SHA_BEFORE="$(sha256sum "$ZRAM_UNIT" | awk '{print $1}')"
	[[ "$ZRAM_SHA_BEFORE" == "$ZRAM_BASE_SHA256" || "$ZRAM_SHA_BEFORE" == "$ZRAM_TARGET_SHA256" ]] || {
		echo "The zram unit is customized or unrecognized; refusing replacement." >&2; exit 1;
	}
else
	echo "The zram unit has an unexpected filesystem object type." >&2; exit 1
fi
if [[ "$ZRAM_INSTALL_UNIT" -eq 0 ]]; then
	UPDATE_PATHS=()
	for rel in "${PAYLOAD_PATHS[@]}"; do
		[[ "$rel" == etc/systemd/system/zram-swap.service ]] || UPDATE_PATHS+=("$rel")
	done
else
	UPDATE_PATHS=("${PAYLOAD_PATHS[@]}")
fi
UPDATE_PATHS+=("home/ark/.config/.VERSION" "home/ark/.config/.update$VERSION" "usr/share/plymouth/themes/text.plymouth")

WIFI_UNIT="$(root_path etc/systemd/system/wifi_importer.service)"
WIFI_LINK="$(root_path etc/systemd/system/multi-user.target.wants/wifi_importer.service)"
ES_DROPIN="$(root_path etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf)"
WIFI_UNIT_EXISTS=0
WIFI_LINK_EXISTS=0
if [[ -e "$WIFI_UNIT" || -L "$WIFI_UNIT" ]]; then
	[[ -f "$WIFI_UNIT" && ! -L "$WIFI_UNIT" ]] || { echo "Existing Wi-Fi unit is not a regular file." >&2; exit 1; }
	[[ "$(sha256sum "$WIFI_UNIT" | awk '{print $1}')" == "$WIFI_SERVICE_SHA256" ]] || {
		echo "Existing Wi-Fi unit differs from the reviewed importer; refusing replacement." >&2; exit 1;
	}
	WIFI_UNIT_EXISTS=1
fi
if [[ -e "$ES_DROPIN" || -L "$ES_DROPIN" ]]; then
	[[ -f "$ES_DROPIN" && ! -L "$ES_DROPIN" && "$(sha256sum "$ES_DROPIN" | awk '{print $1}')" == "${EXPECTED_SHA[etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf]}" ]] || {
		echo "Existing EmulationStation drop-in differs from the reviewed file; refusing replacement." >&2; exit 1;
	}
fi
if [[ -e "$WIFI_LINK" || -L "$WIFI_LINK" ]]; then
	[[ -L "$WIFI_LINK" && "$(readlink "$WIFI_LINK")" == "$WIFI_LINK_TARGET" ]] || {
		echo "Existing Wi-Fi enablement path differs; refusing replacement." >&2; exit 1;
	}
	WIFI_LINK_EXISTS=1
fi
WIFI_ENABLED_BEFORE="$(systemctl is-enabled wifi_importer.service 2>/dev/null || true)"
if [[ "$WIFI_UNIT_EXISTS" -eq 1 && -z "$WIFI_ENABLED_BEFORE" ]]; then
	echo "Could not determine existing Wi-Fi service enablement policy." >&2; exit 1
fi
ZRAM_ENABLED_BEFORE="$(systemctl is-enabled zram-swap.service 2>/dev/null || true)"
ZRAM_ACTIVE_BEFORE="$(systemctl is-active zram-swap.service 2>/dev/null || true)"
if [[ "$ZRAM_INSTALL_UNIT" -eq 1 ]]; then
	[[ -n "$ZRAM_ENABLED_BEFORE" && -n "$ZRAM_ACTIVE_BEFORE" ]] || {
		echo "Could not determine zram enabled/active state." >&2; exit 1;
	}
fi

# Reject symlinked parents so installation and rollback cannot escape ROOT_DIR.
for rel in "${UPDATE_PATHS[@]}"; do
	parent="$(dirname "$rel")"
	current="$ROOT_DIR"
	IFS='/' read -r -a parts <<< "$parent"
	for part in "${parts[@]}"; do
		[[ -n "$part" ]] || continue
		current="${current%/}/$part"
		[[ ! -L "$current" ]] || { echo "Managed path has a symlinked parent: $rel" >&2; exit 1; }
	done
done

# New/dedicated targets may be absent or regular files. Never remove a directory,
# device, or symlink at an ordinary file target. Zram and Wi-Fi are guarded above.
for rel in "${PAYLOAD_PATHS[@]}" "home/ark/.config/.VERSION" "usr/share/plymouth/themes/text.plymouth"; do
	[[ "$rel" == etc/systemd/system/multi-user.target.wants/wifi_importer.service ]] && continue
	[[ "$rel" == etc/systemd/system/zram-swap.service && "$ZRAM_INSTALL_UNIT" -eq 0 ]] && continue
	[[ -e "$(root_path "$rel")" ]] || continue
	[[ -f "$(root_path "$rel")" && ! -L "$(root_path "$rel")" ]] || {
		echo "Managed file target has an unexpected type: /$rel" >&2; exit 1;
	}
done

# Existing files retain their numeric owner/mode when stored on a POSIX
# filesystem. New files use the reviewed payload mode and root ownership.
# VFAT/exFAT ownership and modes are mount policy; never call chown/chmod there.
declare -A TARGET_UID TARGET_GID TARGET_MODE TARGET_FSTYPE
filesystem_type_for() {
	local target="$1" probe="$1"
	while [[ ! -e "$probe" && ! -L "$probe" && "$probe" != / ]]; do probe="$(dirname "$probe")"; done
	findmnt -n -T "$probe" -o FSTYPE
}
for rel in "${PAYLOAD_PATHS[@]}" "home/ark/.config/.VERSION" "usr/share/plymouth/themes/text.plymouth"; do
	[[ "$rel" == etc/systemd/system/multi-user.target.wants/wifi_importer.service ]] && continue
	[[ "$rel" == etc/systemd/system/zram-swap.service && "$ZRAM_INSTALL_UNIT" -eq 0 ]] && continue
	path="$(root_path "$rel")"
	TARGET_FSTYPE[$rel]="$(filesystem_type_for "$path")"
	if [[ -f "$path" && ! -L "$path" ]]; then
		read -r uid gid mode < <(stat -c '%u %g %a' "$path")
		TARGET_UID["$rel"]="$uid"
		TARGET_GID["$rel"]="$gid"
		TARGET_MODE["$rel"]="$mode"
	else
		TARGET_UID["$rel"]=0
		TARGET_GID["$rel"]=0
		if [[ -n "${EXPECTED_MODE[$rel]:-}" ]]; then TARGET_MODE["$rel"]="${EXPECTED_MODE[$rel]}"; else TARGET_MODE["$rel"]=644; fi
	fi
done

current="$ROOT_DIR"
IFS='/' read -r -a backup_parts <<< "$ROM_ROOT/backup/darkosre-update/$VERSION"
for part in "${backup_parts[@]}"; do
	[[ -n "$part" ]] || continue
	current="${current%/}/$part"
	[[ ! -L "$current" ]] || { echo "Rollback path contains a symlink: $current" >&2; exit 1; }
done
mkdir -p "$BACKUP_BASE"
touch "$BACKUP_BASE/.write-test" && rm -f "$BACKUP_BASE/.write-test" || {
	echo "Cannot write rollback data to the selected ROM card." >&2; exit 1;
}

AVAILABLE_TMP_KB="$(df -Pk "${TMPDIR:-/tmp}" | awk 'NR == 2 {print $4}')"
AVAILABLE_ROOT_KB="$(df -Pk "$(root_path opt)" | awk 'NR == 2 {print $4}')"
AVAILABLE_CARD_KB="$(df -Pk "$BACKUP_BASE" | awk 'NR == 2 {print $4}')"
if [[ "${AVAILABLE_TMP_KB:-0}" -lt 50000 || "${AVAILABLE_ROOT_KB:-0}" -lt 20000 || "${AVAILABLE_CARD_KB:-0}" -lt 20000 ]]; then
	echo "Insufficient temporary, system, or ROM-card free space." >&2; exit 1
fi

STAGE=""
BACKUP_ARCHIVE="$BACKUP_BASE/rollback.tar"
BACKUP_READY="$BACKUP_BASE/backup-ready"
BACKUP_SHA_FILE="$BACKUP_BASE/rollback.sha256"
MANAGED_FILE="$BACKUP_BASE/managed-paths.txt"
EXISTED_FILE="$BACKUP_BASE/existed-paths.txt"
INSTALL_STARTED=0
INSTALL_SUCCESS=0

rollback() {
	local failed=0 rel
	for rel in "${UPDATE_PATHS[@]}"; do rm -rf -- "$(root_path "$rel")" || failed=1; done
	if [[ -f "$BACKUP_ARCHIVE" ]]; then
		while IFS= read -r rel; do
			[[ -n "$rel" ]] || continue
			fstype="$(filesystem_type_for "$(root_path "$rel")" 2>/dev/null || true)"
			case "$fstype" in
				vfat|exfat|msdos)
					tar --no-same-owner --no-same-permissions -xpf "$BACKUP_ARCHIVE" -C "$ROOT_DIR" -- "$rel" || failed=1
					;;
				*) tar --numeric-owner -xpf "$BACKUP_ARCHIVE" -C "$ROOT_DIR" -- "$rel" || failed=1 ;;
			esac
		done < "$EXISTED_FILE"
	fi
	systemctl daemon-reload || failed=1
	return "$failed"
}

cleanup() {
	local status=$?
	trap - EXIT
	if [[ "$INSTALL_STARTED" -eq 1 && "$INSTALL_SUCCESS" -ne 1 ]]; then
		echo "Runtime installation failed; restoring $BACKUP_BASE." >&2
		if rollback; then echo "Rollback restored the previous managed paths." >&2
		else echo "Rollback reported an error; preserve $BACKUP_BASE for recovery." >&2; status=1; fi
	fi
	if [[ -n "$STAGE" ]]; then rm -rf -- "$STAGE"; fi
	exit "$status"
}
trap cleanup EXIT

python3 - "$ZIP_PATH" "$0" "${PAYLOAD_PATHS[@]}" <<'PY'
import hashlib, pathlib, stat, sys, zipfile

zip_path, installer_path, *targets = sys.argv[1:]
expected = {
    "usr/local/bin/ppsspp.sh": ("file", "9cc6ab8a1c82154950d52f61f3a223cfc5b66d8b9ec373ea1b2e3637ab5d89e8", 0o755, None),
    "usr/local/bin/importwifi.sh": ("file", "e2dfeee2ac467a9f1385f87351e6af7ce2285360d4b6bd040b9113fa72054667", 0o755, None),
    "usr/local/bin/zram-autostart.sh": ("file", "93a21e451328f1dfd99f8338762a877e176de0d7525074fe484b7f07754e8ea8", 0o755, None),
    "opt/system/Advanced/Restore Default PPSSPP Controls.sh": ("file", "e8aea06956a61256f8efb1cd2db61c5bb60004424cfafd3c651078faa04487d6", 0o755, None),
    "opt/system/ZRam Manager.sh": ("file", "3e10b3d41a80c9b8223f3adda507fd37b3c2bc9c134da5c4fc58defb458b5d18", 0o755, None),
    "etc/systemd/system/wifi_importer.service": ("file", "726e2b2356278fd46035091772f28703ee9e5d6f2bf04bbff7e3ec9d512387fd", 0o644, None),
    "etc/systemd/system/multi-user.target.wants/wifi_importer.service": ("symlink", None, None, "/etc/systemd/system/wifi_importer.service"),
    "etc/systemd/system/emulationstation.service.d/20-r36-nice-limit.conf": ("file", "ed4bf4264b6e298454688d84fa253da69f83b7cdc661a46f1de8895a38566bbc", 0o644, None),
    "etc/systemd/system/zram-swap.service": ("file", "6429ec1445eb16e865c633112579fa90ca7c634fff0cc4cb5e08ed481be7af3e", 0o644, None),
    "opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini": ("file", "83dcbc75635a88dba815fc423fc87b2404a70d339e49e442e802af92a481c537", 0o755, None),
    "opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini": ("file", "56da9d455359d6968fe95e9f0be3c3628772a002999b76eb8f10c398d317e490", 0o755, None),
    "opt/ppsspp/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl": ("file", "56da9d455359d6968fe95e9f0be3c3628772a002999b76eb8f10c398d317e490", 0o755, None),
    "opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/controls.ini": ("file", "83dcbc75635a88dba815fc423fc87b2404a70d339e49e442e802af92a481c537", 0o755, None),
    "opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini": ("file", "078caec2702eab56a4f657fea8fa6f5954dc29249195a77b4b7b3091744ee777", 0o755, None),
    "opt/ppsspp-2021/backupforromsfolder/ppsspp/PSP/SYSTEM/ppsspp.ini.sdl": ("file", "078caec2702eab56a4f657fea8fa6f5954dc29249195a77b4b7b3091744ee777", 0o755, None),
    "usr/local/bin/bigpemu.sh": ("file", "aa14e7c92c6ec2d5bfe41643054d68a9fce24e225625e7901a4eb5625e471ccc", 0o755, None),
    "usr/local/bin/perfmax": ("file", "9a8c45cac25bf76dc0dd8bdda5c2b7c98f08f610481dbaaea6da4cf5fb3d8fab", 0o755, None),
    "usr/local/bin/perfnorm": ("file", "f83e458db52c6f14ab66d62e4d2e4605fda7d2b91dc31b13f0c16fa6e8ab3295", 0o755, None),
    "opt/ppsspp/assets/gamecontrollerdb.txt": ("file", "741a2b21cc85c12c58f1edbe325d610b09fb81d872b9fb3fbb84c4abf86159c5", 0o644, None),
}
if set(targets) != set(expected):
    raise SystemExit("installer payload allowlist does not match its embedded integrity map")
parents = set()
for name in (*expected, "install-runtime.sh"):
    parent = pathlib.PurePosixPath(name).parent
    while parent.parts:
        parents.add(parent.as_posix())
        parent = parent.parent
allowed = set(expected) | parents | {"install-runtime.sh"}
with zipfile.ZipFile(zip_path) as archive:
    if archive.testzip() is not None:
        raise SystemExit("runtime ZIP has a corrupt member")
    seen = set()
    target_seen = set()
    for info in archive.infolist():
        name = info.filename
        normalized = name.rstrip("/")
        parts = pathlib.PurePosixPath(normalized).parts
        if (not name or name.startswith("/") or "\\" in name or
                not normalized or any(part in ("", ".", "..") for part in parts)):
            raise SystemExit(f"unsafe ZIP path: {name!r}")
        if normalized in seen:
            raise SystemExit(f"duplicate ZIP member: {name!r}")
        seen.add(normalized)
        if normalized not in allowed:
            raise SystemExit(f"unexpected ZIP member: {name!r}")
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if normalized in expected:
            target_seen.add(normalized)
            expected_kind, expected_sha, expected_mode, expected_target = expected[normalized]
            data = archive.read(info)
            if expected_kind == "symlink":
                if kind != stat.S_IFLNK or data.decode("utf-8") != expected_target:
                    raise SystemExit(f"symlink type/target mismatch: {name!r}")
            else:
                if kind not in (0, stat.S_IFREG):
                    raise SystemExit(f"payload object is not a regular file: {name!r}")
                if stat.S_IMODE(mode) != expected_mode:
                    raise SystemExit(f"payload mode mismatch: {name!r}")
                if hashlib.sha256(data).hexdigest() != expected_sha:
                    raise SystemExit(f"payload SHA-256 mismatch: {name!r}")
        elif normalized == "install-runtime.sh":
            if kind not in (0, stat.S_IFREG) or archive.read(info) != pathlib.Path(installer_path).read_bytes():
                raise SystemExit("embedded installer differs from executed installer")
        else:
            if kind != stat.S_IFDIR:
                raise SystemExit(f"unexpected non-directory ZIP parent: {name!r}")
    if target_seen != set(expected):
        missing = sorted(set(expected) - target_seen)
        raise SystemExit(f"runtime ZIP is missing expected target(s): {missing}")
    if "install-runtime.sh" not in seen:
        raise SystemExit("runtime ZIP is missing install-runtime.sh")
PY

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/r36-runtime.XXXXXX")"
unzip -q "$ZIP_PATH" -d "$STAGE"
for rel in \
	"usr/local/bin/ppsspp.sh" \
	"usr/local/bin/importwifi.sh" \
	"usr/local/bin/zram-autostart.sh" \
	"opt/system/Advanced/Restore Default PPSSPP Controls.sh" \
	"opt/system/ZRam Manager.sh" \
	"usr/local/bin/bigpemu.sh" \
	"usr/local/bin/perfmax" \
	"usr/local/bin/perfnorm"; do
	bash -n "$STAGE/$rel"
done

for rel in "${PAYLOAD_PATHS[@]}"; do
	parent="$(dirname "$rel")"
	current="$ROOT_DIR"
	IFS='/' read -r -a parts <<< "$parent"
	for part in "${parts[@]}"; do
		[[ -n "$part" ]] || continue
		current="${current%/}/$part"
		mkdir -p "$current"
		[[ ! -L "$current" ]] || { echo "Staged target parent became a symlink: $rel" >&2; exit 1; }
	done
done

if [[ -e "$BACKUP_READY" ]]; then
	[[ -f "$MANAGED_FILE" && -f "$EXISTED_FILE" && -f "$BACKUP_ARCHIVE" && -f "$BACKUP_SHA_FILE" ]] || {
		echo "Existing rollback marker is incomplete; preserve it for manual review." >&2; exit 1;
	}
	cmp -s <(printf '%s\n' "${UPDATE_PATHS[@]}") "$MANAGED_FILE" || {
		echo "Existing rollback snapshot has a different managed-path list." >&2; exit 1;
	}
	(cd "$BACKUP_BASE" && sha256sum -c rollback.sha256)
	tar -tf "$BACKUP_ARCHIVE" >/dev/null
	if [[ "$ZRAM_INSTALL_UNIT" -eq 1 ]]; then
		BACKUP_ZRAM_SHA="$(tar -xOf "$BACKUP_ARCHIVE" etc/systemd/system/zram-swap.service 2>/dev/null | sha256sum | awk '{print $1}')"
		[[ "$BACKUP_ZRAM_SHA" == "$ZRAM_BASE_SHA256" ]] || {
			echo "Existing rollback snapshot does not contain the accepted original zram unit." >&2; exit 1;
		}
	fi
else
	if [[ "$ZRAM_INSTALL_UNIT" -eq 1 ]]; then
		[[ "$ZRAM_SHA_BEFORE" == "$ZRAM_BASE_SHA256" ]] || {
		echo "The zram unit already has the new hash but there is no verified original rollback snapshot." >&2; exit 1;
		}
	fi
	[[ ! -e "$BACKUP_BASE" || -z "$(find "$BACKUP_BASE" -mindepth 1 -maxdepth 1 -print -quit)" ]] || {
		echo "Rollback destination is nonempty but has no verified snapshot." >&2; exit 1;
	}
	printf '%s\n' "${UPDATE_PATHS[@]}" > "$MANAGED_FILE"
	: > "$EXISTED_FILE"
	EXISTED_PATHS=()
	for rel in "${UPDATE_PATHS[@]}"; do
		if [[ -e "$(root_path "$rel")" || -L "$(root_path "$rel")" ]]; then
			EXISTED_PATHS+=("$rel")
			printf '%s\n' "$rel" >> "$EXISTED_FILE"
		fi
	done
	if ((${#EXISTED_PATHS[@]})); then
		tar --numeric-owner -cpf "$BACKUP_ARCHIVE.tmp" -C "$ROOT_DIR" -- "${EXISTED_PATHS[@]}"
	else
		tar -cpf "$BACKUP_ARCHIVE.tmp" --files-from=/dev/null
	fi
	tar -tf "$BACKUP_ARCHIVE.tmp" >/dev/null
	mv "$BACKUP_ARCHIVE.tmp" "$BACKUP_ARCHIVE"
	(cd "$BACKUP_BASE" && sha256sum rollback.tar > rollback.sha256)
	touch "$BACKUP_READY"
fi

if [[ "$WIFI_UNIT_EXISTS" -eq 1 ]]; then
	# Existing identical service: preserve its exact enablement policy. A missing
	# multi-user link means disabled here; no new link is introduced.
	INSTALL_WIFI_LINK=0
else
	# Fresh install: the staged target intentionally enables the new oneshot.
	INSTALL_WIFI_LINK=1
fi

INSTALL_STARTED=1
for rel in "${PAYLOAD_PATHS[@]}"; do
	[[ "$rel" == etc/systemd/system/zram-swap.service && "$ZRAM_INSTALL_UNIT" -eq 0 ]] && continue
	if [[ "$rel" == etc/systemd/system/multi-user.target.wants/wifi_importer.service ]]; then
		if [[ "$WIFI_LINK_EXISTS" -eq 1 || "$INSTALL_WIFI_LINK" -eq 0 ]]; then continue; fi
		mkdir -p "$(dirname "$(root_path "$rel")")"
		ln -s "$WIFI_LINK_TARGET" "$(root_path "$rel")"
		continue
	fi
	tmp="$(root_path "$rel").runtime-tmp.$$"
	cp "$STAGE/$rel" "$tmp"
	case "${TARGET_FSTYPE[$rel]}" in
		vfat|exfat|msdos) ;;
		*)
			chmod "${TARGET_MODE[$rel]}" "$tmp"
			if [[ "$EUID" -eq 0 ]]; then chown "${TARGET_UID[$rel]}:${TARGET_GID[$rel]}" "$tmp"; fi
			;;
	esac
	mv -fT "$tmp" "$(root_path "$rel")"
done

systemctl daemon-reload
ZRAM_ENABLED_AFTER="$(systemctl is-enabled zram-swap.service 2>/dev/null || true)"
ZRAM_ACTIVE_AFTER="$(systemctl is-active zram-swap.service 2>/dev/null || true)"
if [[ "$ZRAM_INSTALL_UNIT" -eq 1 ]]; then
	[[ "$ZRAM_ENABLED_AFTER" == "$ZRAM_ENABLED_BEFORE" && "$ZRAM_ACTIVE_AFTER" == "$ZRAM_ACTIVE_BEFORE" ]] || {
		echo "Zram service enablement/activity changed unexpectedly." >&2; exit 1;
	}
elif [[ "$ZRAM_UNIT_STATE" == absent ]]; then
	[[ ! -e "$ZRAM_UNIT" && ! -L "$ZRAM_UNIT" ]] || { echo "An absent zram unit appeared during install." >&2; exit 1; }
elif [[ "$ZRAM_UNIT_STATE" == masked ]]; then
	[[ -L "$ZRAM_UNIT" && "$(readlink "$ZRAM_UNIT")" == /dev/null ]] || { echo "A masked zram unit changed during install." >&2; exit 1; }
fi
WIFI_ENABLED_AFTER="$(systemctl is-enabled wifi_importer.service 2>/dev/null || true)"
if [[ "$WIFI_UNIT_EXISTS" -eq 1 ]]; then
	[[ "$WIFI_ENABLED_AFTER" == "$WIFI_ENABLED_BEFORE" ]] || {
		echo "Existing Wi-Fi service enablement changed unexpectedly." >&2; exit 1;
	}
else
	[[ "$WIFI_ENABLED_AFTER" == enabled ]] || {
		echo "New Wi-Fi importer did not retain its declared enabled state." >&2; exit 1;
	}
fi

ROM_PATHS_AFTER="$(grep -o '<path>[^<]*</path>' "$ES_CONFIG")"
ES_CONFIG_SHA_AFTER="$(sha256sum "$ES_CONFIG" | awk '{print $1}')"
SWITCH_SHA_AFTER="$(sha256sum "$SWITCH_SD2" "$SWITCH_MAIN")"
[[ "$ROM_PATHS_BEFORE" == "$ROM_PATHS_AFTER" && "$ES_CONFIG_SHA_BEFORE" == "$ES_CONFIG_SHA_AFTER" && "$SWITCH_SHA_BEFORE" == "$SWITCH_SHA_AFTER" ]] || {
	echo "ROM paths, ES configuration, or SD-switch scripts changed unexpectedly." >&2; exit 1;
}

printf '%s\n' "$VERSION" > "$VERSION_FILE"
touch "$NEW_MARKER"
sed -i "/title=/c\\title=dArkOSRE ($VERSION)" "$PLYMOUTH_FILE"
INSTALL_SUCCESS=1
if ! systemctl reboot; then INSTALL_SUCCESS=0; echo "System reboot request failed; restoring the previous system state." >&2; exit 1; fi
echo "Installed the scoped runtime draft for /$ROM_ROOT. Rollback is retained at $BACKUP_BASE."
