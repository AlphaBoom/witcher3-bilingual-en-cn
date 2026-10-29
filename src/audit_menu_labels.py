"""Read all relevant menu Flash assets and script keys; never modify assets."""
import json
import re
import struct
import zlib
from collections import defaultdict
from pathlib import Path
from menu_english_rules import key_hash
from w3strings_v164 import Bank

folder = Path(__file__).resolve().parent
root = folder.parent
report = json.loads((folder / 'report.json').read_text('utf-8-sig'))
en = Bank.parse((folder / report['backup_directory'] / 'en.w3strings').read_bytes())
keys = {h: sid ^ en.magic for h, sid in struct.iter_unpack('<II', en.keys)}
references = defaultdict(set)
pages = {'common', 'worldmap', 'glossary', 'character', 'alchemy', 'crafting',
         'inventory', 'repair', 'journal', 'meditation'}
asset_count = 0
for path in sorted((root / 'content/content0/bundles').glob('*.bundle')):
    with path.open('rb') as stream:
        header = stream.read(32)
        if header[:8] != b'POTATO70':
            continue
        index = stream.read(struct.unpack_from('<I', header, 16)[0])
        for start in range(0, len(index), 304):
            row = index[start:start + 304]
            name = row[:256].split(b'\0')[0].decode('utf-8').replace('\\', '/')
            if not name.endswith('.redswf') or not any('/swf/' + page + '/' in name for page in pages):
                continue
            offset, size, compressed, crc, codec = struct.unpack_from('<QIIII', row, 272)
            assert codec in (0, 1)
            stream.seek(offset)
            raw = stream.read(compressed)
            data = zlib.decompress(raw) if codec == 1 else raw
            assert len(data) == size
            position = data.find(b'CFX')
            if position >= 0:
                data = zlib.decompress(data[position + 8:])
            asset_count += 1
            for key in set(x.decode('ascii') for x in re.findall(rb'[A-Za-z_][A-Za-z0-9_]{4,100}', data)):
                if key_hash(key) in keys:
                    references[key].add(name)

script_tabs = set()
for path in (root / 'content/content0/scripts/game/gui/menus').rglob('*.ws'):
    text = path.read_text('utf-8-sig')
    for key in re.findall(r'["\']([A-Za-z_][A-Za-z0-9_]{4,100})["\']', text):
        if key_hash(key) in keys:
            references[key].add(str(path.relative_to(root)))
    script_tabs.update(re.findall(r'DefineMenuItem\(\s*\'[^\']+\',\s*"([^"]+)"', text))

rows = [{'key': key, 'id': keys[key_hash(key)], 'en': en.texts.get(keys[key_hash(key)], ''),
         'sources': sorted(sources), 'declared_navigation_tab': key in script_tabs}
        for key, sources in sorted(references.items())]
for row in (json.loads((folder / 'ui-key-audit.json').read_text('utf-8')) if (folder / 'ui-key-audit.json').exists() else []):
    key = row['key']
    if key not in references and key_hash(key) in keys:
        sid = keys[key_hash(key)]
        rows.append({'key': key, 'id': sid, 'en': en.texts.get(sid, ''),
                     'sources': ['previous read-only GUI key audit'], 'declared_navigation_tab': False})
rows.sort(key=lambda row: row['key'])
(folder / 'full-menu-label-audit.json').write_text(json.dumps({'flash_assets_read': asset_count, 'keys': rows}, ensure_ascii=False, indent=2), 'utf-8')
old = set(json.loads((folder / 'menu_english_keys.json').read_text('utf-8')))
missing = [row for row in rows if row['key'] not in old and len(row['en']) < 65 and
           (row['key'].lower().startswith(('input', 'panel_map', 'panel_character', 'panel_button', 'panel_title', 'panel_alchemy_tab', 'panel_inventory_tab')) or 'tab' in row['key'].lower())]
print(json.dumps({'assets': asset_count, 'known_keys': len(rows), 'candidates': [{k: row[k] for k in ('key', 'id', 'en', 'declared_navigation_tab')} for row in missing]}, ensure_ascii=False))

# The user authorizes English UI throughout menus. Keep story, journal entry,
# item name/description and ability-effect keys outside this namespace policy.
prefixes = ('panel_', 'menu_', 'gui_', 'input', 'controllayout_', 'photomode_',
            'ui_', 'options_', 'mods_', 'press_any_key_', 'save_slot_type_')
protected_prefixes = ('panel_buff_', 'panel_title_buff_')
selected = old.copy()
for row in rows:
    key = row['key'].lower()
    if (row['declared_navigation_tab'] or key.startswith(prefixes)) and not key.startswith(protected_prefixes):
        selected.add(row['key'])
(folder / 'menu_english_keys.json').write_text(json.dumps(sorted(selected), ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps({'selected_english_ui_keys': len(selected), 'selection_policy': 'UI namespaces and declared tabs; gameplay description keys excluded'}))
