def convert(d):
    return b''.join(d[i:i+4][::-1] for i in range(0, len(d) & ~3, 4)) + d[len(d) & ~3:]
