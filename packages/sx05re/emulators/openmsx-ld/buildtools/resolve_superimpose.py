#!/usr/bin/env python3
# Resolve "#if SUPERIMPOSE" preprocessor blocks in installed openMSX shaders
# to a fixed branch (GLES shader compiler has no support for these defines).
# Usage: resolve_superimpose.py <shader-dir> <branch>
#   branch 0 -> keep the #else part (no superimpose, regular openmsx)
#   branch 1 -> keep the #if part  (superimpose, laserdisc video)
import sys, os, re

sdir = sys.argv[1]
branch = int(sys.argv[2])
group = 1 if branch == 1 else 2

for fn in os.listdir(sdir):
    if not (fn.endswith('.frag') or fn.endswith('.vert')):
        continue
    fpath = os.path.join(sdir, fn)
    src = open(fpath).read()
    if '#if' not in src:
        continue
    src = re.sub(r'#if SUPERIMPOSE[^\n]*\n(.*?)(?:#else[^\n]*\n(.*?))?#endif[^\n]*\n',
        lambda m: (m.group(group) or '').strip() + '\n', src, flags=re.DOTALL)
    src = re.sub(r'#define SUPERIMPOSE [01]\n', '', src)
    open(fpath, 'w').write(src)
    print('Resolved (branch %d):' % branch, fn)
