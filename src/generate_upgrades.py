"""Derive English upgrade names from the user's local XML definitions and bank."""
import argparse
import json
from pathlib import Path
import re
import struct
import zlib
from menu_english_rules import key_hash
from w3strings_v164 import Bank


def generate(folder, english_bank):
    en = Bank.parse(english_bank.read_bytes())
    keys = {h: sid ^ en.magic for h, sid in struct.iter_unpack('<II', en.keys)}
    items = {}
    for path in sorted((folder.parent / 'content/content0/bundles').glob('*.bundle')):
        with path.open('rb') as stream:
            header = stream.read(32)
            if header[:8] != b'POTATO70':
                continue
            index = stream.read(struct.unpack_from('<I', header, 16)[0])
            for start in range(0, len(index), 304):
                row = index[start:start + 304]
                name = row[:256].split(b'\0')[0].decode('utf-8').replace('\\', '/')
                if not name.endswith('.xml') or '/items' not in name:
                    continue
                offset, size, compressed, crc, codec = struct.unpack_from('<QIIII', row, 272)
                assert codec in (0, 1), name
                stream.seek(offset)
                data = stream.read(compressed)
                data = zlib.decompress(data) if codec == 1 else data
                assert len(data) == size
                text = re.sub(r'<!--.*?-->', '', data.decode('utf-8-sig'), flags=re.S)
                for tag in re.findall(r'<item\s[^>]*>', text):
                    attrs = dict(re.findall(r'([A-Za-z_]+)\s*=\s*"([^"]*)"', tag))
                    if 'name' in attrs:
                        items.setdefault(attrs['name'].lower(), {}).update(attrs)

    def attribute(item, key, seen=None):
        seen = set() if seen is None else seen
        if item in seen:
            return None
        seen.add(item)
        attrs = items.get(item, {})
        return attrs.get(key) or (attribute(attrs['template'].lower(), key, seen) if 'template' in attrs else None)

    rows = []
    for item in sorted(items):
        if attribute(item, 'category') != 'upgrade':
            continue
        key = attribute(item, 'localisation_key_name')
        assert key and key_hash(key) in keys, item
        sid = keys[key_hash(key)]
        assert en.texts.get(sid, '').strip(), item
        rows.append({'item': item, 'key': key, 'id': sid, 'en': en.texts[sid]})
    assert rows, 'No upgrade definitions found'
    script = (folder / 'scripts/bilingual_base.ws').read_text('utf-8')
    script += '\n// Generated locally from original English upgrade names.\n'
    script += 'function BilingualEnCnEnglishUpgradeName(itemName : name, fallbackText : string) : string\n{\n    switch (StrLower(NameToString(itemName)))\n    {\n'
    for row in rows:
        script += '        case ' + json.dumps(row['item'], ensure_ascii=False) + ': return ' + json.dumps(row['en'], ensure_ascii=False) + ';\n'
    script += '    }\n    return fallbackText;\n}\n\n'
    script += (folder / 'scripts/socket_wrapper.ws').read_text('utf-8')
    (folder / 'prepared').mkdir(exist_ok=True)
    (folder / 'prepared/bilingual_placeholders.ws').write_text(script, 'utf-8')
    (folder / 'remove-upgrade-name-audit.json').write_text(json.dumps({'upgrades': rows}, ensure_ascii=False, indent=2), 'utf-8')
    print('Generated English names for', len(rows), 'socket upgrades.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--english-bank', required=True, type=Path)
    generate(Path(__file__).resolve().parent, parser.parse_args().english_bank)
