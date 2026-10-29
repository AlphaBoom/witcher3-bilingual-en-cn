"""Local Witcher 3 Remastered v164 reader/writer; no third-party executables.
Format references:
https://github.com/WolvenKit/WolvenKit-7/blob/master/WolvenKit.W3Strings/W3StringFile.cs
https://github.com/Odashikonbu/w3strings-rust/blob/master/src/file.rs
v164 uses UTF-8 byte offsets/lengths and advances the XOR key for each byte.
"""
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import hashlib
import json
import struct

MAGICS = {0x43975139: 0x79321793, 0: 0, 0x18632176: 0x16875467}


def read_count(data, pos):
    first = data[pos]
    if first == 128:
        return 0, pos + 1
    result = shift = 0
    for i in range(1, 7):
        b = data[pos]
        pos += 1
        bits = 7 if b > 127 else 6
        mask = 127 if b > 127 else 63 if b > 63 and i == 1 else 255
        result |= (b & mask) << shift
        shift += bits
        if b < 64 or (i >= 3 and b < 128):
            return result, pos
    raise ValueError('Invalid count')


def write_count(n):
    assert n >= 0
    if n == 0:
        return b'\x80'
    if n < 64:
        return bytes([n])
    out = bytearray([(n & 63) | 64])
    n >>= 6
    while n >= 128:
        out.append((n & 127) | 128)
        n >>= 7
    # A two-byte count needs an unambiguous terminator (<64), otherwise
    # the first continuation byte is marked and a third byte is added.
    if len(out) == 1 and n >= 64:
        out.append(n | 128)
        out.append(0)
    else:
        out.append(n)
    return bytes(out)


def crypt(raw, magic):
    if magic == 0:
        return raw
    sk = (magic >> 8) & 65535
    out = bytearray(len(raw))
    for i, b in enumerate(raw):
        out[i] = b ^ (((len(raw) + 1) * sk) & 255)
        sk = ((sk << 1) | (sk >> 15)) & 65535
    return bytes(out)


@dataclass
class Bank:
    header: bytes
    tail: bytes
    magic: int
    entries: list
    keys: bytes
    key_count: int
    texts: dict

    @classmethod
    def parse(cls, data):
        assert data[:4] == b'RTSW'
        assert struct.unpack_from('<I', data, 4)[0] == 164, 'Only Remastered v164 is supported'
        k1 = struct.unpack_from('<H', data, 8)[0]
        k2 = struct.unpack_from('<H', data, len(data) - 2)[0]
        magic = MAGICS[(k1 << 16) | k2]
        count, pos = read_count(data, 10)
        entries = list(struct.iter_unpack('<III', data[pos:pos + count * 12]))
        pos += count * 12
        key_count, pos = read_count(data, pos)
        keys = data[pos:pos + key_count * 8]
        pos += key_count * 8
        payload_count, pos = read_count(data, pos)
        assert len(data) == pos + payload_count + 2, 'Unexpected trailing data'
        texts = {}
        for hashed_id, offset, length in entries:
            assert offset + length < payload_count
            assert data[pos + offset + length] == 0, 'Missing terminator'
            sid = hashed_id ^ magic
            assert sid not in texts, 'Duplicate ID'
            texts[sid] = crypt(data[pos + offset:pos + offset + length], magic).decode('utf-8')
        return cls(data[:10], data[-2:], magic, entries, keys, key_count, texts)

    def build(self, replacements=None):
        replacements = self.texts if replacements is None else replacements
        assert set(replacements) == set(self.texts), 'IDs changed'
        payload = bytearray()
        locations = {}
        # Retain the original physical order as well as the lookup table order.
        for hashed_id, _, _ in sorted(self.entries, key=lambda row: row[1]):
            sid = hashed_id ^ self.magic
            raw = replacements[sid].encode('utf-8')
            locations[hashed_id] = (len(payload), len(raw))
            payload.extend(crypt(raw, self.magic))
            payload.append(0)
        rows = bytearray()
        for hashed_id, _, _ in self.entries:
            offset, length = locations[hashed_id]
            rows.extend(struct.pack('<III', hashed_id, offset, length))
        return (self.header + write_count(len(self.entries)) + rows
                + write_count(self.key_count) + self.keys
                + write_count(len(payload)) + payload + self.tail)


def inspect():
    root = Path(__file__).resolve().parents[1]
    banks = {}
    for code in ('en', 'cn'):
        path = root / 'content' / 'content0' / (code + '.w3strings')
        original = path.read_bytes()
        bank = Bank.parse(original)
        rebuilt = bank.build()
        reread = Bank.parse(rebuilt)
        assert reread.texts == bank.texts
        assert reread.keys == bank.keys
        print(json.dumps({'language': code, 'strings': len(bank.texts),
                          'keys': bank.key_count, 'original_bytes': len(original),
                          'rebuilt_bytes': len(rebuilt),
                          'byte_identical_roundtrip': original == rebuilt,
                          'sha256': hashlib.sha256(original).hexdigest()}))
        banks[code] = bank
    en, cn = banks['en'], banks['cn']
    common = en.texts.keys() & cn.texts.keys()
    print(json.dumps({'matched_ids': len(common), 'en_only': len(en.texts.keys()-cn.texts.keys()),
                      'cn_only': len(cn.texts.keys()-en.texts.keys()),
                      'same_text': sum(en.texts[k] == cn.texts[k] for k in common)}))
    examples = []
    for sid in common:
        a, b = en.texts[sid], cn.texts[sid]
        if 30 <= len(a) < 100 and any('\u4e00' <= c <= '\u9fff' for c in b) and '<' not in a and '<' not in b:
            examples.append({'id': sid, 'english': a, 'chinese': b})
            if len(examples) >= 6:
                break
    print(json.dumps(examples, ensure_ascii=False))


if __name__ == '__main__':
    inspect()
