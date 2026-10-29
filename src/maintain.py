"""Local-only update workflow; does not download or distribute game resources."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'update', 'install', 'restore'])
    parser.add_argument('--game-dir', required=True, type=Path)
    parser.add_argument('--settings-path', type=Path)
    parser.add_argument('--install', action='store_true', help='Install after successful update validation')
    args = parser.parse_args()
    root = args.game_dir.resolve()
    exe = root / 'bin/x64_dx12/witcher3.exe'
    if not exe.is_file():
        parser.error('Expected bin/x64_dx12/witcher3.exe in --game-dir')
    # Pass the path as environment data, never as PowerShell source text.
    version = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        '(Get-Item -LiteralPath $env:BICN_GAME_EXE).VersionInfo.FileVersion.Split("(")[0].Trim()'],
        env={**os.environ, 'BICN_GAME_EXE': str(exe)}, text=True).strip()
    folder = root / '_bilingual_en_cn'
    report_file = folder / 'report.json'
    report = json.loads(report_file.read_text('utf-8-sig')) if report_file.exists() else None
    current = sha(root / 'content/content0/cn.w3strings')
    if args.action == 'check':
        state = 'unmanaged'
        if report:
            if current == report['output_sha256']:
                state = 'installed' if version == report['game_version'] else 'game-updated'
            elif current == report['source_sha256']['cn']:
                state = 'original-text'
            else:
                state = 'game-updated-or-file-changed'
        print(json.dumps({'game_version': version, 'state': state}, ensure_ascii=False))
        return
    if args.action == 'update':
        if report and current == report['output_sha256'] and version != report['game_version']:
            raise RuntimeError('Executable updated but the old bilingual bank is still installed. Restore current vanilla language files with Steam before rebuilding.')
        src = Path(__file__).resolve().parent
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        if folder.exists():
            snapshot = folder / 'history' / ('before-tool-update-' + stamp)
            snapshot.mkdir(parents=True)
            for name in ['report.json', 'installed.json', 'menu_english_keys.json', 'prepare_bilingual.py', 'install.ps1', 'restore.ps1']:
                if (folder / name).is_file():
                    shutil.copy2(folder / name, snapshot / name)
            if (folder / 'prepared/bilingual_placeholders.ws').is_file():
                shutil.copy2(folder / 'prepared/bilingual_placeholders.ws', snapshot / 'bilingual_placeholders.ws')
        folder.mkdir(exist_ok=True)
        for path in src.iterdir():
            if path.suffix in ('.py', '.json', '.ps1'):
                shutil.copy2(path, folder / path.name)
        # Preserve any locally expanded UI rules when deploying a newer tool.
        if report and (snapshot / 'menu_english_keys.json').exists():
            old = json.loads((snapshot / 'menu_english_keys.json').read_text('utf-8-sig'))
            new = json.loads((folder / 'menu_english_keys.json').read_text('utf-8-sig'))
            (folder / 'menu_english_keys.json').write_text(json.dumps(sorted(set(old) | set(new)), indent=2), 'utf-8')
        (folder / 'scripts').mkdir(exist_ok=True)
        for name in ('bilingual_base.ws', 'socket_wrapper.ws'):
            shutil.copy2(src.parent / 'scripts' / name, folder / 'scripts' / name)
        reuse = report and version == report['game_version']
        backup = report['backup_directory'] if reuse else 'backups/' + version + '_' + stamp
        if reuse:
            english_bank = folder / backup / 'en.w3strings'
        else:
            english_bank = root / 'content/content0/en.w3strings'
        run(sys.executable, folder / 'generate_upgrades.py', '--english-bank', english_bank)
        options = ['--game-version', version, '--backup-dir', backup]
        if reuse:
            options.append('--use-backup')
        run(sys.executable, folder / 'prepare_bilingual.py', *options)
        run(sys.executable, folder / 'audit_menu_labels.py')
        run(sys.executable, folder / 'prepare_bilingual.py', '--game-version', version,
            '--backup-dir', backup, '--use-backup')
        run(sys.executable, folder / 'validate_release.py')
        if not args.install:
            print('Prepared and validated. Run install when ready.')
            return
    if args.action in ('install', 'update'):
        run(sys.executable, folder / 'validate_release.py')
    command = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
               folder / ('restore.ps1' if args.action == 'restore' else 'install.ps1')]
    if args.settings_path:
        command.extend(['-SettingsPath', args.settings_path.resolve()])
    run(*command)


if __name__ == '__main__':
    main()
