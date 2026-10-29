"""Classify bilingual separators from vanilla resource references, not length.

W3Strings has no per-entry rendering flag. Voiced subtitle IDs come from the
W3Speech index. Journal property types distinguish titles from descriptions.
Unknown fields stay inline; this avoids injecting HTML into a plain text field.

Read-only format references:
https://github.com/WolvenKit/WolvenKit-7/blob/main/WolvenKit.W3Speech/Coder.cs
https://github.com/WolvenKit/WolvenKit-7/blob/main/WolvenKit.Bundles/BundleItem.cs
https://gist.github.com/rfuzzo/6e7a0669a7f8140d28a281b16bb3cb0f
"""
from collections import defaultdict
import hashlib
import re
import struct
import zlib
from w3strings_v164 import MAGICS, read_count

BREAK_TAG = re.compile(r'(?<!<)<(?:br\s*/?|/?p(?:\s[^<>]*)?)>', re.IGNORECASE)


def speech_ids(root):
    ids = set()
    sources = []
    for path in sorted((root / 'content').rglob('enpc.w3speech')):
        size = path.stat().st_size
        with path.open('rb') as stream:
            header = stream.read(20)
            assert header[:4] == b'CPSW'
            assert struct.unpack_from('<I', header, 4)[0] == 164
            count, start = read_count(header, 10)
            assert start + count * 40 + 2 <= size
            stream.seek(start)
            index = stream.read(count * 40)
            tail = stream.read(2)
        magic = MAGICS[(struct.unpack_from('<H', header, 8)[0] << 16) | struct.unpack('<H', tail)[0]]
        for sid, high, wave_offset, wave_size, lipsync_offset, lipsync_size in struct.iter_unpack('<IIQQQQ', index):
            assert wave_offset >= start + len(index) + 2
            assert wave_offset + wave_size <= size
            assert lipsync_offset + lipsync_size <= size
            ids.add(sid ^ magic)
        sources.append({'path': str(path.relative_to(root)), 'entries': count,
                        'index_sha256': hashlib.sha256(header[:start] + index + tail).hexdigest()})
    assert sources, 'No English speech index available to classify subtitles'
    return ids, sources


def journal_strings(data):
    assert data[:4] == b'CR2W'
    tables = list(struct.iter_unpack('<III', data[40:160]))
    string_start, string_size, _ = tables[0]
    strings = data[string_start:string_start + string_size]
    name_start, name_count, _ = tables[1]
    # Some legacy editor identifiers contain non-UTF-8 bytes. They are never
    # used for classification; class, property and type names are ASCII.
    names = [strings[offset:].split(b'\0')[0].decode('utf-8', 'replace')
             for offset, _ in struct.iter_unpack('<II', data[name_start:name_start + name_count * 8])]
    chunk_start, chunk_count, _ = tables[4]
    for classname, flags, parent, length, start, template, crc in struct.iter_unpack('<HHIIIII', data[chunk_start:chunk_start + chunk_count * 24]):
        assert data[start] == 0 and start + length <= len(data)
        pos, end = start + 1, start + length
        while pos + 2 <= end:
            field = struct.unpack_from('<H', data, pos)[0]
            if field == 0:
                break
            typename, size = struct.unpack_from('<HI', data, pos + 2)
            assert size >= 4 and pos + 4 + size <= end
            if names[typename] == 'LocalizedString':
                assert size == 8
                sid = struct.unpack_from('<I', data, pos + 8)[0]
                if sid:
                    yield sid, names[classname], names[field]
            pos += 4 + size


def journal_ids(root):
    refs = defaultdict(set)
    sources = []
    for path in sorted((root / 'content').rglob('*.bundle')):
        with path.open('rb') as stream:
            header = stream.read(32)
            if header[:8] != b'POTATO70':
                continue
            index_size = struct.unpack_from('<I', header, 16)[0]
            assert index_size % 304 == 0 and index_size <= path.stat().st_size - 32
            index = stream.read(index_size)
            journal_count = 0
            resource_hash = hashlib.sha256()
            for start in range(0, index_size, 304):
                row = index[start:start + 304]
                name = row[:256].split(b'\0')[0].decode('utf-8')
                if not name.endswith('.journal'):
                    continue
                offset, size, compressed_size, crc, codec = struct.unpack_from('<QIIII', row, 272)
                assert codec in (0, 1), f'Unsupported journal compression: {name}'
                assert offset + compressed_size <= path.stat().st_size
                stream.seek(offset)
                raw = stream.read(compressed_size)
                data = zlib.decompress(raw) if codec == 1 else raw
                assert len(data) == size
                resource_hash.update(row)
                resource_hash.update(raw)
                for sid, cls, field in journal_strings(data):
                    refs[sid].add((cls, field))
                journal_count += 1
            if journal_count:
                sources.append({'path': str(path.relative_to(root)), 'resources': journal_count,
                                'journal_sha256': resource_hash.hexdigest()})
    assert sources, 'No journal references available to classify titles'
    return refs, sources


def load_context(root):
    voiced, speech_sources = speech_ids(root)
    journal, journal_sources = journal_ids(root)
    inline = {sid for sid, refs in journal.items()
              if any(field in ('title', 'name') for cls, field in refs)}
    rich = {sid for sid, refs in journal.items()
            if any(field == 'description' for cls, field in refs)}
    return {'voiced': voiced, 'inline': inline, 'rich': rich,
            'sources': {'speech': speech_sources, 'journal': journal_sources},
            'journal_references': journal}


def separator(sid, primary, secondary, context):
    # Reused title/description IDs receive the safer inline representation.
    if sid in context['inline']:
        return ' / ', 'journal_title_or_name'
    if sid in context['voiced']:
        return '<br>', 'voiced_subtitle'
    if sid in context['rich']:
        return '<br>', 'journal_description'
    if BREAK_TAG.search(primary) or BREAK_TAG.search(secondary):
        return '<br>', 'vanilla_multiline_markup'
    return ' / ', 'unconfirmed_field_inline'
