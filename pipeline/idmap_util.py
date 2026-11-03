"""PS3 -> PC asset ID map (base game). Words equal to a known PS3 asset ID are replaced by the PC ID."""
import json, os, struct
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'asset_idmap.json')
IDMAP = {int(k, 16): int(v, 16) for k, v in json.load(open(_p)).items()} if os.path.exists(_p) else {}
_s = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sev_idmap.json')   # Severed assets replaced by same-name PC assets
if os.path.exists(_s):
    IDMAP.update({int(k, 16): int(v, 16) for k, v in json.load(open(_s)).items()})
def remap_words_le(buf, start=0, end=None):
    """buf: bytearray in PC (LE) layout; remap aligned u32 words that are known PS3 IDs."""
    end = len(buf) if end is None else end
    for o in range(start, end - 3, 4):
        v = struct.unpack_from('<I', buf, o)[0]
        if v in IDMAP: struct.pack_into('<I', buf, o, IDMAP[v])
