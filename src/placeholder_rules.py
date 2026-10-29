"""Keep positional formatting arguments separate from bilingual translation."""
from collections import Counter
import re

TOKEN = re.compile(r'\$([ISFs])\$')
INDEXED = re.compile(r'\$BICN_([ISF])(\d+)\$')

# Repairs are limited to incorrect placeholder contracts in vanilla CN.
CN_REPAIRS = {
    1129122: '炸弹伤害变为原来的三倍，但装备栏中的炸弹数量减半。不会造成伤害的炸弹不受影响。',
    1135386: '用剑打出的致命一击产生 1 点肾上腺素。',
    1458253: '在闪躲或翻滚成功后，下次连续进行的 $I$ 次速攻额外造成 30% 伤害。',
    1458254: '在闪躲或翻滚成功后，下次连续进行的 $I$ 次速攻额外造成 30% 伤害。',
}


def normalize(text):
    # Vanilla crafting_bonus_set_title uses lowercase s, but the formatter
    # only recognises uppercase S. All other tokens/tags stay untouched.
    return text.replace('$s$', '$S$')


def counts(text):
    return Counter(m.group(1) for m in TOKEN.finditer(normalize(text)))


def index_secondary(primary, secondary, sid):
    primary = normalize(primary)
    secondary = normalize(secondary)
    assert counts(primary) == counts(secondary), f'Placeholder mismatch at {sid}'
    indices = Counter()

    def replace(match):
        kind = match.group(1)
        index = indices[kind]
        indices[kind] += 1
        return f'$BICN_{kind}{index}$'

    secondary = TOKEN.sub(replace, secondary)
    assert not TOKEN.search(secondary), f'Unprotected secondary token at {sid}'
    return primary, secondary
