"""Batch: port Severed streams (report only, or --write) and append per-stream results to report.csv."""
import os, sys, csv, time, faulthandler
faulthandler.enable()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_str
G = os.path.expanduser('~/mnt/Dead Space 2'); W = os.path.expanduser('~/weller1')
streams = sorted(os.path.relpath(os.path.join(dp, f), W) for dp, dn, fn in os.walk(W) if not dp.startswith(os.path.join(W, 'clod')) for f in fn if f.lower().endswith('.str'))
start, end = int(sys.argv[1]), int(sys.argv[2]); budget = float(sys.argv[3]) if len(sys.argv) > 3 else 160
write = '--write' in sys.argv
pc = port_str.PCAssets(G, os.path.join(G, 'pc_assets.csv'))
t0 = time.time(); done = 0
with open('report2.csv' if write else 'report.csv', 'a', newline='') as f:
    w = csv.writer(f)
    for i in range(start, min(end, len(streams))):
        if time.time() - t0 > budget: break
        rel = streams[i]
        out, rep = port_str.port(open(os.path.join(W, rel), 'rb').read(), pc)
        if write:
            dst = os.path.join('out', rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(out)
        if True:
            for nm, t, how, n, note in rep:
                w.writerow([i, rel.replace('/', '\\'), nm, t, how, n, note])
        done = i + 1
print('streams', len(streams), 'done up to', done, 'in %.0fs' % (time.time() - t0))
