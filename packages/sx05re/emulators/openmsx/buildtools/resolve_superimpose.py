#!/usr/bin/env python3
# Resolve "#if SUPERIMPOSE" preprocessor blocks in installed openMSX shaders
# to their SUPERIMPOSE=0 branch (GLES has no preprocessor support for these).
# Usage: resolve_superimpose.py <shader-dir>
import sys, os, re

sdir = sys.argv[1]
for fn in os.listdir(sdir):
    if not (fn.endswith('.frag') or fn.endswith('.vert')):
        continue
    fpath = os.path.join(sdir, fn)
    src = open(fpath).read()
    if '#if' not in src:
        continue
    src = re.sub(r'#if SUPERIMPOSE[^\n]*\n(.*?)(?:#else[^\n]*\n(.*?))?#endif[^\n]*\n',
        lambda m: (m.group(2) or '').strip() + '\n', src, flags=re.DOTALL)
    src = re.sub(r'#define SUPERIMPOSE [01]\n', '', src)
    open(fpath, 'w').write(src)
    print('Resolved:', fn)
