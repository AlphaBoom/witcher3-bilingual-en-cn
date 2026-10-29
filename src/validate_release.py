"""Validate local generated data without relying on developer history files."""
import hashlib
import json
from pathlib import Path
import re
import struct
from placeholder_rules import normalize, counts, INDEXED, TOKEN
from menu_english_rules import key_hash
from w3strings_v164 import Bank


def validate(folder):
    report = json.loads((folder / 'report.json').read_text('utf-8-sig'))
    backup = folder / report['backup_directory']
    en = Bank.parse((backup / 'en.w3strings').read_bytes())
    cn = Bank.parse((backup / 'cn.w3strings').read_bytes())
    raw = (folder / 'prepared/cn.w3strings').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == report['output_sha256']
    out = Bank.parse(raw)
    assert out.build() == raw
    assert (en.texts.keys() | cn.texts.keys()) <= out.texts.keys()
    enkeys = {h: sid ^ en.magic for h, sid in struct.iter_unpack('<II', en.keys)}
    outkeys = dict(struct.iter_unpack('<II', out.keys))
    assert dict(struct.iter_unpack('<II', cn.keys)).items() <= outkeys.items()
    names = json.loads((folder / 'menu_english_keys.json').read_text('utf-8'))
    for name in names:
        h = key_hash(name)
        assert out.texts[outkeys[h]] == normalize(en.texts[enkeys[h]]), name
    dynamic = 0
    for sid, text in out.texts.items():
        if not INDEXED.search(text):
            continue
        dynamic += 1
        assert counts(text) == counts(en.texts[sid]), sid
        args = {kind: [f'ARG_{kind}_{i}_END' for i in range(count)] for kind, count in counts(text).items()}
        for nbsp in ('', '&nbsp;'):
            indexes = dict.fromkeys(args, 0)
            def original(match):
                kind = match[1]
                value = args[kind][indexes[kind]]
                indexes[kind] += 1
                return nbsp + value
            rendered = TOKEN.sub(original, text)
            rendered = INDEXED.sub(lambda m: nbsp + args[m[1]][int(m[2])], rendered)
            assert not INDEXED.search(rendered) and not TOKEN.search(rendered)
            assert all(rendered.count(nbsp + value) == 2 for values in args.values() for value in values)
    assert dynamic == report['dynamic_bilingual_entries']
    script = (folder / report['script_mod']['prepared_file']).read_text('utf-8')
    assert hashlib.sha256(script.encode('utf-8')).hexdigest() == report['script_mod']['sha256']
    wrappers = re.findall(r'@wrapMethod(?:\((\w+)\))?\s+function\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*(\w+))?\s*\{', script)
    assert len(wrappers) == len(re.findall(r'@wrapMethod\b', script)) == 3
    sources = {'': folder.parent / 'content/content0/scripts/game/localizedContent.ws',
               'W3GuiSocketsInventoryComponent': folder.parent / 'content/content0/scripts/game/gui/_old/components/guiSocketsInventoryComponent.ws'}
    for cls, method, params, result in wrappers:
        original = re.search(r'\bfunction\s+' + method + r'\s*\(([^)]*)\)\s*(?::\s*(\w+))?\s*\{', sources[cls].read_text('utf-8-sig'))
        assert original, (cls, method)
        compact = lambda s: re.sub(r'\s+', '', s).lower()
        assert compact(params) == compact(original[1])
        assert (result or 'void') == (original[2] or 'void')
    cases = {json.loads(item): json.loads(text) for item, text in re.findall(r'case ("(?:[^"\\]|\\.)*"): return ("(?:[^"\\]|\\.)*");', script)}
    upgrades = json.loads((folder / 'remove-upgrade-name-audit.json').read_text('utf-8'))['upgrades']
    for upgrade in upgrades:
        assert cases[upgrade['item']] == en.texts[upgrade['id']]
        # Only the socket list changes: ordinary item labels retain Chinese.
        sid = outkeys[key_hash(upgrade['key'])]
        assert any('\u3400' <= c <= '\u9fff' for c in out.texts[sid]), upgrade['item']
    assert 'W3GuiDisassembleInventoryComponent' not in script and 'W3StandaloneDismantleComponent' not in script
    summary = {'game_version': report['game_version'], 'english_ui_keys': len(names),
               'dynamic_bilingual_entries': dynamic, 'socket_upgrade_names': len(upgrades),
               'wrapper_signatures': len(wrappers), 'in_game_verified': False}
    (folder / 'release-validation.json').write_text(json.dumps(summary, indent=2), 'utf-8')
    print(json.dumps(summary))


if __name__ == '__main__':
    validate(Path(__file__).resolve().parent)
