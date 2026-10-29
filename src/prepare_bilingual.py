"""Generate and validate English-first/Simplified-Chinese bilingual v164 data.
Only writes preparation files. install.ps1 applies the verified output later.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import re
import shutil
import struct
from collections import Counter
from w3strings_v164 import Bank
from placeholder_rules import CN_REPAIRS, INDEXED, counts, index_secondary, normalize
from rendering_rules import load_context, separator as select_separator
from menu_english_rules import price_ids

folder = Path(__file__).resolve().parent
root = folder.parent
originals = {}
banks = {}
parser = argparse.ArgumentParser()
parser.add_argument('--game-version', required=True)
parser.add_argument('--backup-dir', required=True)
parser.add_argument('--use-backup', action='store_true', help='Regenerate from checksum-verified vanilla backups after installation')
args = parser.parse_args()
backup = (folder / args.backup_dir).resolve()
assert backup.is_relative_to(folder), 'Backup must stay inside preparation directory'
backup.mkdir(parents=True, exist_ok=True)
previous_report = None
if args.use_backup:
    previous_report = json.loads((folder / 'report.json').read_text('utf-8-sig'))
    assert previous_report['game_version'] == args.game_version
    assert (folder / previous_report['backup_directory']).resolve() == backup
previous_output_hash = None
for code in ('en', 'cn'):
    path = root / 'content' / 'content0' / (code + '.w3strings')
    dest = backup / (code + '.w3strings')
    current = path.read_bytes()
    if args.use_backup:
        original = dest.read_bytes()
        assert hashlib.sha256(original).hexdigest() == previous_report['source_sha256'][code]
        current_hash = hashlib.sha256(current).hexdigest()
        allowed = {previous_report['source_sha256'][code]}
        if code == 'cn':
            allowed.add(previous_report['output_sha256'])
            # A preparation run can be repeated before the previous run is
            # installed; the checksum-verified installed predecessor is valid.
            if previous_report.get('previous_output_sha256'):
                allowed.add(previous_report['previous_output_sha256'])
            if current_hash != previous_report['source_sha256'][code]:
                previous_output_hash = current_hash
        assert current_hash in allowed, 'Installed source changed; stop for inspection'
    else:
        original = current
        if dest.exists():
            assert dest.read_bytes() == original, 'Existing backup differs; stop for inspection'
        else:
            shutil.copy2(path, dest)
    assert dest.read_bytes() == original
    bank = Bank.parse(original)
    assert bank.build() == original, 'Original did not round-trip byte-for-byte'
    originals[code] = original
    banks[code] = bank

en, cn = banks['en'], banks['cn']
english = dict(en.texts)
chinese = dict(cn.texts)
enkeys = {h: sid ^ en.magic for h, sid in struct.iter_unpack('<II', en.keys)}
cnkeys = dict(struct.iter_unpack('<II', cn.keys))
aliases = []
for key in enkeys.keys() & cnkeys.keys():
    a, b = enkeys[key], cnkeys[key]
    if a != b and a in en.texts and b in cn.texts:
        english[b] = en.texts[a]
        if a not in chinese:
            chinese[a] = cn.texts[b]
        aliases.append((key, a, b))

for sid, text in CN_REPAIRS.items():
    assert sid in chinese and sid in english
    chinese[sid] = text
# Repair a malformed duration phrase without changing parameter order.
assert '每点肾上腺素值 $S$s + $S$s' in chinese[1066917]
chinese[1066917] = chinese[1066917].replace('>持续时间：每点肾上腺素值 $S$s + $S$s。',
                                          '持续时间：$S$ 秒，每点肾上腺素额外增加 $S$ 秒。')

def has_chinese(text):
    return any('\u3400' <= c <= '\u9fff' or '\uf900' <= c <= '\ufaff' for c in text)

merged = {}
changed = bilingual = dynamic_bilingual = 0
rendering_context = load_context(root)
rendering_counts = Counter()
rendering_audit = {}
english_only_ids = price_ids(enkeys, cnkeys)
for sid in en.texts.keys() | cn.texts.keys():
    primary = english.get(sid, '')
    secondary = chinese.get(sid, '')
    if sid in english_only_ids:
        merged[sid] = normalize(primary)
    elif primary.strip() and secondary.strip() and has_chinese(secondary) and primary.strip() != secondary.strip():
        primary, secondary = index_secondary(primary, secondary, sid)
        # Renderer capability is independent of string length and tag case.
        separator, rendering_reason = select_separator(sid, primary, secondary, rendering_context)
        rendering_counts[rendering_reason] += 1
        rendering_audit[sid] = rendering_reason
        merged[sid] = primary + separator + secondary
        bilingual += 1
        dynamic_bilingual += bool(INDEXED.search(secondary))
        assert merged[sid].startswith(primary)
        assert merged[sid].endswith(secondary)
    else:
        merged[sid] = normalize(primary if primary.strip() else secondary)
    changed += merged[sid] != cn.texts.get(sid)

keys = dict(cnkeys)
for key in enkeys.keys() - cnkeys.keys():
    keys[key] = enkeys[key]
menu_english_lookups = {'enabled': False, 'reason': 'Menu UI reads original English-only keys; Remove Upgrade uses exact English names from XML item definitions'}
# CN has an unencrypted, sorted lookup table, including all vanilla IDs.
entries = [(sid, i, 0) for i, sid in enumerate(sorted(merged))]
key_bytes = b''.join(struct.pack('<II', key, sid) for key, sid in sorted(keys.items()))
output_bank = Bank(cn.header, cn.tail, 0, entries, key_bytes, len(keys), merged)
encoded = output_bank.build()
reread = Bank.parse(encoded)
assert reread.texts == merged
assert set(cn.texts) <= set(reread.texts)
assert set(en.texts) <= set(reread.texts)
assert dict(struct.iter_unpack('<II', reread.keys)).items() >= cnkeys.items()
prepared = folder / 'prepared'
prepared.mkdir(exist_ok=True)
output_path = prepared / 'cn.w3strings'
output_path.write_bytes(encoded)
assert output_path.read_bytes() == encoded
(folder / 'rendering-audit.json').write_text(json.dumps(rendering_audit, sort_keys=True), encoding='utf-8')
script_path = prepared / 'bilingual_placeholders.ws'
script_bytes = script_path.read_bytes()
script_bytes.decode('utf-8')

for sid, text in merged.items():
    if INDEXED.search(text):
        # The original formatter must see exactly the English argument count.
        assert counts(text) == counts(english[sid])
        assert not re.search(r'\$s\$', text)

samples = []
for sid in (524318, 1048614, 1048584, 1048636, 97959, 97991, 98013, 1062892, 1066914, 1449731, 1066289):
    samples.append({'id': sid, 'text': merged[sid]})
report = {
    'game_version': args.game_version,
    'backup_directory': str(backup.relative_to(folder)),
    'generated_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'format_version': 164,
    'mode': 'English first; Simplified Chinese secondary; English menu UI and Remove Upgrade names',
    'language_slot': 'CN',
    'source_sha256': {c: hashlib.sha256(d).hexdigest() for c, d in originals.items()},
    'output_sha256': hashlib.sha256(encoded).hexdigest(),
    'output_bytes': len(encoded),
    'english_source_entries': len(en.texts),
    'chinese_source_entries': len(cn.texts),
    'output_entries': len(merged),
    'bilingual_entries': bilingual,
    'changed_from_cn': changed,
    'lookup_keys': len(keys),
    'lookup_aliases_resolved': len(aliases),
    'validation': ['original byte-identical round-trip for EN and CN',
                   'output decoded equals every intended string',
                   'all EN and CN source IDs retained',
                   'every original CN lookup key retained',
                   'UTF-8 payload, v164 header and language keys preserved',
                   'dynamic CN arguments indexed separately; original EN argument count retained',
                   'all bilingual parameter signatures match after targeted vanilla repairs',
                   'bilingual separators selected by speech/journal references and existing multiline markup'],
    'previous_output_sha256': previous_output_hash,
    'dynamic_bilingual_entries': dynamic_bilingual,
    'placeholder_fixes': [*CN_REPAIRS, 1066917, 1213793],
    'rendering_policy': 'Voiced subtitles, journal descriptions and existing multiline HTML: br; journal titles/names and unconfirmed fields: inline slash',
    'rendering_categories': dict(rendering_counts),
    'rendering_source_metadata': rendering_context['sources'],
    'rendering_audit_file': 'rendering-audit.json',
    'english_only_original_ids': sorted(english_only_ids),
    'menu_ui_english_key_count': len(json.loads((folder / 'menu_english_keys.json').read_text('utf-8'))),
    'menu_ui_key_audit': 'full-menu-label-audit.json',
    'menu_ui_policy': 'English UI labels, buttons, filters, tabs and menu messages; item/ability descriptions and journal/story texts stay bilingual',
    'menu_english_lookups': menu_english_lookups,
    'context_only_english': ['Remove Upgrade socket-item names'],
    'script_mod': {
        'relative_path': 'mods/modBilingualEnCnPlaceholders/content/scripts/local/bilingual_placeholders.ws',
        'prepared_file': 'prepared/bilingual_placeholders.ws',
        'sha256': hashlib.sha256(script_bytes).hexdigest(),
    },
    'samples': samples,
    'in_game_visual_verification': False,
    'game_script_compilation_verified': False,
}
(folder / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k not in ('samples', 'source_sha256')}, ensure_ascii=False))
print(json.dumps(samples, ensure_ascii=False))
