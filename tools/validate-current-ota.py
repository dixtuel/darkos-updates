#!/usr/bin/env python3
"""Validate maintained R36 OTA payloads; do not infer device compatibility."""
import hashlib
import pathlib
import re
import stat
import struct
import subprocess
import sys
import zipfile


def validate(archive_path):
    archive_path = pathlib.Path(archive_path)
    manifest = archive_path.parent / 'SHA256SUMS'
    expected = [line.split() for line in manifest.read_text().splitlines() if line.strip()]
    hashes = {name.lstrip('*'): digest for digest, name in expected}
    actual = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if hashes.get(archive_path.name) != actual:
        raise ValueError(f'{archive_path}: checksum mismatch')
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f'{archive_path}: corrupt entry')
        names = set()
        symlinks = set()
        for info in archive.infolist():
            name = info.filename
            parts = name.rstrip('/').split('/')
            if not name or name.startswith('/') or '\\' in name or any(p in ('', '.', '..') for p in parts):
                raise ValueError(f'unsafe ZIP path: {name!r}')
            canonical = name.rstrip('/')
            if canonical in names:
                raise ValueError(f'duplicate ZIP path: {name!r}')
            names.add(canonical)
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK):
                raise ValueError(f'unsupported ZIP object: {name!r}')
            if kind == stat.S_IFDIR or info.is_dir():
                continue
            data = archive.read(info)
            if kind == stat.S_IFLNK:
                symlinks.add(canonical)
                target = data.decode('utf-8')
                if not target or '\\' in target or '..' in target.split('/'):
                    raise ValueError(f'unsafe symlink: {name!r}')
                if target.startswith('/') and (canonical, target) not in {
                    ('etc/systemd/system/multi-user.target.wants/r36-disable-mali-opencl-aliases.service',
                     '/etc/systemd/system/r36-disable-mali-opencl-aliases.service'),
                    ('etc/systemd/system/multi-user.target.wants/wifi_importer.service',
                     '/etc/systemd/system/wifi_importer.service'),
                }:
                    raise ValueError(f'unexpected absolute symlink: {name!r}')
                continue
            if name.endswith('.sh'):
                syntax = subprocess.run(['bash', '-n'], input=data, capture_output=True)
                if syntax.returncode:
                    raise ValueError(f'invalid shell syntax: {name!r}: '
                                     f'{syntax.stderr.decode("utf-8", "replace").strip()}')
            if re.search(r'(^|/)lib[^/]*\.so(?:\.|$)', name) or name == 'opt/DSperate/dsperate':
                if len(data) < 20 or data[:4] != b'\x7fELF':
                    raise ValueError(f'empty or invalid ELF: {name!r}')
            if data[:4] == b'\x7fELF':
                if len(data) < 20 or data[5] != 1:
                    raise ValueError(f'unsupported ELF header: {name!r}')
                machine = struct.unpack_from('<H', data, 18)[0]
                if name.startswith('usr/lib/aarch64-linux-gnu/') or name == 'opt/DSperate/dsperate':
                    if (data[4], machine) != (2, 183):
                        raise ValueError(f'wrong AArch64 ABI: {name!r}')
                elif name.startswith('usr/lib/arm-linux-gnueabihf/'):
                    if (data[4], machine) != (1, 40):
                        raise ValueError(f'wrong ARMhf ABI: {name!r}')
        # Replacing the whole modern PPSSPP assets directory must retain its
        # controller database and UI assets, not merely a loadable executable.
        if 'opt/ppsspp/PPSSPPSDL' in names:
            required_assets = {
                'opt/ppsspp/assets/gamecontrollerdb.txt',
                'opt/ppsspp/assets/compat.ini',
                'opt/ppsspp/assets/lang/en_US.ini',
                'opt/ppsspp/assets/font_atlas.meta',
                'opt/ppsspp/assets/font_atlas.zim',
                'opt/ppsspp/assets/ui_atlas.meta',
                'opt/ppsspp/assets/ui_atlas.zim',
            }
            missing = required_assets - names
            if missing:
                raise ValueError(f'PPSSPP required assets missing: {sorted(missing)}')
            for required in required_assets:
                if required in symlinks or not archive.read(required):
                    raise ValueError(f'PPSSPP required asset is linked/empty: {required}')
        for name in names:
            parts = name.split('/')
            if any('/'.join(parts[:i]) in symlinks for i in range(1, len(parts))):
                raise ValueError(f'entry beneath symlink: {name!r}')
    print(f'{archive_path}: checksum, structure and ELF checks passed ({len(names)} entries)')


if __name__ == '__main__':
    for argument in sys.argv[1:]:
        validate(argument)
    if len(sys.argv) < 2:
        raise SystemExit('usage: validate-current-ota.py ARCHIVE [ARCHIVE ...]')
