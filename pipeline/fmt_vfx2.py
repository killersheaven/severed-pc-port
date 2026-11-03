"""VFX (.vfb) PS3 -> PC, component-aware (2026-10-16). Rules in vfx_rules2.json, learned from 3,003 base-game pairs
(keys: component tag/version/flags + offset from tag or from the last '####' string anchor; header fields and the
36-byte entry table; asset IDs after '####'). Held-out (half/half): 1,489/1,501 files exact; the rest 1-bit float
rounding, 3 .flr colour words, 1 content difference."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfx2
_M = vfx2.Model(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vfx_rules2.json'))))
def convert(d):
    return _M.convert(d)
def coverage(d):
    """fraction of words whose action came from a learned rule (not the fallback guess)"""
    K = vfx2.keys(d); n = len(K)
    return sum(any(repr(k) in _M.R for k in ks) for ks in K.values()) / max(n, 1)
