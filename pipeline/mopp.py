"""MOPP code walker (opcode table from the PC exe's hkpMoppFindAllVirtualMachine, 0x1531C70)."""
LEN = {0x00: 1, 0x05: None, 0x06: None, 0x07: None, 0x09: 2, 0x0a: 3, 0x0b: 5, 0x50: 2, 0x51: 3, 0x52: 4, 0x53: 5}
for o in range(1, 5): LEN[o] = 4
for o in range(0x10, 0x1d): LEN[o] = 4
for o in (0x20, 0x21, 0x22): LEN[o] = 3
for o in (0x23, 0x24, 0x25): LEN[o] = 7
for o in (0x26, 0x27, 0x28): LEN[o] = 3
for o in (0x29, 0x2a, 0x2b): LEN[o] = 7
for o in range(0x30, 0x50): LEN[o] = 1
for o in range(0x60, 0x64): LEN[o] = 2
for o in range(0x64, 0x68): LEN[o] = 3
for o in range(0x68, 0x6c): LEN[o] = 5
def walk(code):
    """returns (unknown opcodes Counter, terminal count, max offset reached)"""
    import collections
    bad = collections.Counter(); term = 0; seen = set(); stack = [0]
    while stack:
        i = stack.pop()
        while 0 <= i < len(code) and i not in seen:
            seen.add(i); op = code[i]
            if op not in LEN: bad[op] += 1; break
            if op == 0x00: break
            if op == 0x05: i += 2 + code[i+1]; continue
            if op == 0x06: i += 3 + (code[i+1] << 8 | code[i+2]); continue
            if op == 0x07: i += 4 + (code[i+1] << 16 | code[i+2] << 8 | code[i+3]); continue
            if 0x10 <= op <= 0x1c: stack.append(i + 4 + code[i+3]); i += 4; continue
            if 0x20 <= op <= 0x22: stack.append(i + 3 + code[i+2]); i += 3; continue
            if 0x23 <= op <= 0x25:
                j1 = code[i+3] << 8 | code[i+4]; j2 = code[i+5] << 8 | code[i+6]
                stack.append(i + 7 + j2); i = i + 7 + j1; continue
            if 0x30 <= op <= 0x53 and (op < 0x50 or op >= 0x50):
                if op >= 0x30 and op <= 0x4f or op in (0x50, 0x51, 0x52, 0x53): term += 1; break
            i += LEN[op]
    return bad, term, len(seen)
