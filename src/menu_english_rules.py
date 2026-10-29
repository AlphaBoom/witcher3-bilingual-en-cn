"""Menu UI policy; original item-name IDs stay bilingual."""
import struct
from placeholder_rules import normalize

PREFIX = '__bicn_english_'
PRICE_KEYS = ('attribute_name_price', 'panel_inventory_item_price')


def key_hash(text):
    value = 0
    for byte in text.lower().encode('utf-8'):
        value = (value * 31 + byte) & 0xffffffff
    return value


def alias_name(original_hash):
    return PREFIX + str(original_hash >> 16) + '_' + str(original_hash & 65535)


def price_ids(enkeys, cnkeys=None):
    from pathlib import Path
    import json
    names = set(PRICE_KEYS)
    names.update(json.loads((Path(__file__).parent / 'menu_english_keys.json').read_text('utf-8')))
    result = {enkeys[key_hash(key)] for key in names}
    if cnkeys:
        result.update(cnkeys[key_hash(key)] for key in names if key_hash(key) in cnkeys)
    return result

