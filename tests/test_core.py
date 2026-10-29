import sys
from pathlib import Path
import struct
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from w3strings_v164 import Bank
from placeholder_rules import counts, index_secondary, INDEXED
from rendering_rules import separator


class CoreTests(unittest.TestCase):
    def test_utf8_bank_roundtrip(self):
        texts = {12: 'Synthetic / 合成文本', 99: 'Line<br>另一行 $I$'}
        keys = struct.pack('<II', 12345, 12)
        bank = Bank(b'RTSW' + struct.pack('<I', 164) + b'\0\0', b'\0\0', 0,
                    [(sid, i, 0) for i, sid in enumerate(texts)], keys, 1, texts)
        raw = bank.build()
        decoded = Bank.parse(raw)
        self.assertEqual(decoded.texts, texts)
        self.assertEqual(decoded.keys, keys)
        self.assertEqual(decoded.build(), raw)

    def test_parameter_contract(self):
        primary, secondary = index_secondary('$I$ + $I$ / $S$', '$I$ 加 $I$，$s$', 1)
        self.assertEqual(counts(primary), {'I': 2, 'S': 1})
        self.assertEqual(INDEXED.findall(secondary), [('I', '0'), ('I', '1'), ('S', '0')])
        with self.assertRaises(AssertionError):
            index_secondary('$I$', '$S$', 2)

    def test_renderer_capabilities(self):
        ctx = {'inline': {1}, 'voiced': {1, 2}, 'rich': {3}}
        self.assertEqual(separator(1, 'A', '中', ctx)[0], ' / ')
        self.assertEqual(separator(2, 'A', '中', ctx)[0], '<br>')
        self.assertEqual(separator(3, 'A', '中', ctx)[0], '<br>')
        self.assertEqual(separator(4, 'A<BR>B', '中', ctx)[0], '<br>')
        self.assertEqual(separator(5, 'A', '中', ctx)[0], ' / ')


if __name__ == '__main__':
    unittest.main()
