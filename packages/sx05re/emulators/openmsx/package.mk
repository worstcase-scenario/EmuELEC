PKG_NAME="openmsx"
PKG_VERSION="RELEASE_21_0"
PKG_REV="0"
PKG_ARCH="any"
PKG_LICENSE="GPL"
PKG_SITE="https://github.com/openMSX/openMSX"
PKG_URL="${PKG_SITE}/archive/refs/tags/${PKG_VERSION}.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 SDL2_ttf libpng zlib tcl alsa-lib glew"
PKG_SHORTDESC="openMSX: The MSX emulator that aims for perfection"
PKG_TOOLCHAIN="manual"

pre_configure_target() {
  python3 - "${PKG_BUILD}/src/video/VisibleSurface.cc" << 'PYEOF'
import sys, os

fname = sys.argv[1]
src = open(fname).read()

old = 'void VisibleSurface::finish()\n{\n\tSDL_GL_SwapWindow(window.get());\n}'
new = (
'static GLuint _cur_prog=0,_cur_vbo=0;\n'
'static GLint  _cur_pos=-1;\n'
'static bool   _cur_failed=false;\n'
'static int    _cur_last_x=-1,_cur_last_y=-1;\n'
'static Uint32 _cur_last_move=0;\n'
'static void drawSoftwareCursor(SDL_Window* w)\n'
'{\n'
'    if(_cur_failed) return;\n'
'    GLint curProg=0;\n'
'    glGetIntegerv(GL_CURRENT_PROGRAM,&curProg);\n'
'    if(curProg==0) return;\n'
'    int mx,my,ww,wh;\n'
'    SDL_GetMouseState(&mx,&my);\n'
'    if(mx!=_cur_last_x||my!=_cur_last_y){\n'
'        _cur_last_x=mx; _cur_last_y=my;\n'
'        _cur_last_move=SDL_GetTicks();\n'
'    }\n'
'    if(SDL_GetTicks()-_cur_last_move>3000) return;\n'
'    if(_cur_prog==0){\n'
'        const char* vsh="#version 100\\nattribute vec2 p;\\nvoid main(){gl_Position=vec4(p,0.0,1.0);}\\n";\n'
'        const char* fsh="#version 100\\nprecision mediump float;\\nvoid main(){gl_FragColor=vec4(1.0,1.0,1.0,1.0);}\\n";\n'
'        GLuint vs=glCreateShader(GL_VERTEX_SHADER);\n'
'        glShaderSource(vs,1,&vsh,0); glCompileShader(vs);\n'
'        GLint ok=0; glGetShaderiv(vs,GL_COMPILE_STATUS,&ok);\n'
'        if(!ok){char buf[256];glGetShaderInfoLog(vs,256,0,buf);fprintf(stderr,"CURSOR VS: %s\\n",buf);_cur_failed=true;return;}\n'
'        GLuint fs=glCreateShader(GL_FRAGMENT_SHADER);\n'
'        glShaderSource(fs,1,&fsh,0); glCompileShader(fs);\n'
'        glGetShaderiv(fs,GL_COMPILE_STATUS,&ok);\n'
'        if(!ok){char buf[256];glGetShaderInfoLog(fs,256,0,buf);fprintf(stderr,"CURSOR FS: %s\\n",buf);_cur_failed=true;return;}\n'
'        _cur_prog=glCreateProgram();\n'
'        glAttachShader(_cur_prog,vs); glAttachShader(_cur_prog,fs);\n'
'        glLinkProgram(_cur_prog);\n'
'        glGetProgramiv(_cur_prog,GL_LINK_STATUS,&ok);\n'
'        if(!ok){char buf[256];glGetProgramInfoLog(_cur_prog,256,0,buf);fprintf(stderr,"CURSOR LINK: %s\\n",buf);_cur_failed=true;return;}\n'
'        glDeleteShader(vs); glDeleteShader(fs);\n'
'        _cur_pos=glGetAttribLocation(_cur_prog,"p");\n'
'        glGenBuffers(1,&_cur_vbo);\n'
'    }\n'
'    SDL_GetWindowSize(w,&ww,&wh);\n'
'    if(ww<=0||wh<=0) return;\n'
'    // Save current viewport and override to full window\n'
'    GLint vp[4];\n'
'    glGetIntegerv(GL_VIEWPORT,vp);\n'
'    glViewport(0,0,ww,wh);\n'
'    // Map mouse to full window NDC\n'
'    float cx=(float)mx/ww*2.0f-1.0f;\n'
'    float cy=1.0f-(float)my/wh*2.0f;\n'
'    float sx=0.025f, sy=sx*(float)ww/(float)wh;\n'
'    float v[]={cx,cy, cx+sx,cy-sy*0.5f, cx+sx*0.45f,cy-sy*1.3f};\n'
'    GLint prevVbo;\n'
'    glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&prevVbo);\n'
'    glUseProgram(_cur_prog);\n'
'    glBindBuffer(GL_ARRAY_BUFFER,_cur_vbo);\n'
'    glBufferData(GL_ARRAY_BUFFER,sizeof(v),v,GL_DYNAMIC_DRAW);\n'
'    glEnableVertexAttribArray(_cur_pos);\n'
'    glVertexAttribPointer(_cur_pos,2,GL_FLOAT,GL_FALSE,0,0);\n'
'    glDisable(GL_BLEND);\n'
'    glDisable(GL_DEPTH_TEST);\n'
'    glDrawArrays(GL_TRIANGLES,0,3);\n'
'    glDisableVertexAttribArray(_cur_pos);\n'
'    glBindBuffer(GL_ARRAY_BUFFER,prevVbo);\n'
'    glUseProgram(curProg);\n'
'    glViewport(vp[0],vp[1],vp[2],vp[3]);\n'
'}\n'
'void VisibleSurface::finish()\n'
'{\n'
'    drawSoftwareCursor(window.get());\n'
'    SDL_GL_SwapWindow(window.get());\n'
'}'
)
src_norm = src.replace('\r\n', '\n')
if 'drawSoftwareCursor' in src_norm:
    print("Software cursor patch already applied, skipping"); sys.exit(0)
if old not in src_norm:
    print("WARNING: finish() pattern not found"); sys.exit(1)
open(fname, "w").write(src_norm.replace(old, new, 1))
print("Software cursor patch applied to VisibleSurface.cc")
PYEOF
}

_openmsx_patch() {
  local b="$1"

  grep -rl 'static constexpr std::initializer_list' "${b}/src/" | \
    xargs sed -i 's/static constexpr std::initializer_list/static const std::initializer_list/g'

  sed -i 's/^#define OPENGL_VERSION OPENGL_2_1$/#define OPENGL_VERSION OPENGL_ES_2_0/' \
    "${b}/src/video/GLUtil.hh"

  local g="${b}/src/video/GLUtil.cc"
  sed -i 's/source += "#ifdef GL_FRAGMENT_PRECISION_HIGH.*//g' "${g}"
  sed -i '/"  precision highp float;/d' "${g}"
  sed -i '/"#else/d' "${g}"
  sed -i '/"  precision mediump float;/d' "${g}"
  sed -i 's/"#endif.*/source += "precision highp float;\\n";/' "${g}"

  sed -i \
    's/"#ifdef GL_ES\\n"[[:space:]]*$//;s/"    precision mediump float;\\n"[[:space:]]*$//;s/"#endif\\n"[[:space:]]*$//' \
    "${b}/src/3rdparty/imgui/imgui_impl_opengl3.cc"

  sed -i 's/systemFileContext().resolve(tmpStrCat("shaders/preferSystemFileContext().resolve(tmpStrCat("shaders/g' \
    "${b}/src/video/GLUtil.cc"
}

make_target() {
  pre_configure_target
  local sysroot="${SYSROOT_PREFIX}"
  local real_cxx="${CXX%% *}"
  local wname="$(basename "${real_cxx}")"
  local cxx_dir="${PKG_BUILD}/.cxx"
  local cfg_dir="${PKG_BUILD}/derived/aarch64-linux-opt/config"

  mkdir -p "${sysroot}/usr/include/GL"
  [ -f "${sysroot}/usr/include/GL/glu.h" ] || \
    printf '#ifndef __glu_h__\n#define __glu_h__\n/* GLU stub */\n#endif\n' \
      > "${sysroot}/usr/include/GL/glu.h"

  mkdir -p "${cxx_dir}"
  cat > "${cxx_dir}/${wname}" << PYWRAP
#!/usr/bin/env python3
import sys, os
sysroot = "${sysroot}"
real    = "${real_cxx}"
args = []
for a in sys.argv[1:]:
    if   a.startswith('-I/usr/'): a = '-I' + sysroot + a[2:]
    elif a.startswith('-L/usr/'): a = '-L' + sysroot + a[2:]
    args.append(a)
os.execv(real, [real] + args)
PYWRAP
  chmod +x "${cxx_dir}/${wname}"

  cat > "${PKG_BUILD}/build/probe.py" << 'NOOP'
import sys
sys.exit(0)
NOOP

  mkdir -p "${cfg_dir}"
  cat > "${cfg_dir}/systemfuncs.hh" << SYSFUNCS
#define HAVE_FTRUNCATE 1
#define HAVE_MMAP 1
SYSFUNCS

  cat > "${cfg_dir}/probed_defs.mk" << PROBEDEFS
HAVE_ALSA_H:=true
HAVE_ALSA_LIB:=true
ALSA_CFLAGS:=
ALSA_LDFLAGS:=-lasound
HAVE_FREETYPE_H:=true
HAVE_FREETYPE_LIB:=true
FREETYPE_CFLAGS:=-I${sysroot}/usr/include/freetype2 -I${sysroot}/usr/include
FREETYPE_LDFLAGS:=-L${sysroot}/usr/lib -lfreetype
HAVE_GL_H:=true
HAVE_GL_LIB:=true
GL_CFLAGS:=
GL_LDFLAGS:=-lGL
HAVE_GLEW_H:=true
HAVE_GLEW_LIB:=true
GLEW_CFLAGS:=
GLEW_LDFLAGS:=-lGLEW -lGL
HAVE_OGG_H:=true
HAVE_OGG_LIB:=true
OGG_CFLAGS:=
OGG_LDFLAGS:=-logg
HAVE_PNG_H:=true
HAVE_PNG_LIB:=true
PNG_CFLAGS:=-I${sysroot}/usr/include/libpng16
PNG_LDFLAGS:=-lpng16
HAVE_SDL2_H:=true
HAVE_SDL2_LIB:=true
SDL2_CFLAGS:=-I${sysroot}/usr/include/SDL2 -D_REENTRANT
SDL2_LDFLAGS:=-lSDL2
HAVE_SDL2_TTF_H:=true
HAVE_SDL2_TTF_LIB:=true
SDL2_TTF_CFLAGS:=-I${sysroot}/usr/include/SDL2
SDL2_TTF_LDFLAGS:=-lSDL2_ttf
HAVE_TCL_H:=true
HAVE_TCL_LIB:=true
TCL_CFLAGS:=
TCL_LDFLAGS:=-ltcl8.6
HAVE_THEORA_H:=true
HAVE_THEORA_LIB:=true
THEORA_CFLAGS:=
THEORA_LDFLAGS:=-ltheoradec
HAVE_VORBIS_H:=true
HAVE_VORBIS_LIB:=true
VORBIS_CFLAGS:=
VORBIS_LDFLAGS:=-lvorbis
HAVE_ZLIB_H:=true
HAVE_ZLIB_LIB:=true
ZLIB_CFLAGS:=
ZLIB_LDFLAGS:=-lz
HAVE_FTRUNCATE:=true
HAVE_MMAP:=true
PROBEDEFS

  _openmsx_patch "${PKG_BUILD}"

  make -C ${PKG_BUILD} \
    OPENMSX_TARGET_CPU=${TARGET_ARCH} \
    OPENMSX_TARGET_OS=linux \
    CXX="${cxx_dir}/${wname}" \
    CXXFLAGS="${TARGET_CFLAGS}" \
    INSTALL_BASE=/usr \
    V=1
}

makeinstall_target() {
  local sysroot="${SYSROOT_PREFIX}"
  local real_cxx="${CXX%% *}"
  local wname="$(basename "${real_cxx}")"
  local cxx_dir="${PKG_BUILD}/.cxx"

  make -C ${PKG_BUILD} \
    OPENMSX_TARGET_CPU=${TARGET_ARCH} \
    OPENMSX_TARGET_OS=linux \
    CXX="${cxx_dir}/${wname}" \
    INSTALL_BASE=/usr \
    DESTDIR=${INSTALL} \
    install

  # Resolve SUPERIMPOSE=0 in shaders
  python3 - "${INSTALL}/usr/share/shaders" << 'PYSHADER'
import sys, os, re
sdir = sys.argv[1]
for fn in os.listdir(sdir):
    if not (fn.endswith('.frag') or fn.endswith('.vert')): continue
    fpath = os.path.join(sdir, fn)
    src = open(fpath).read()
    if '#if' not in src: continue
    src = re.sub(r'#if SUPERIMPOSE[^\n]*\n(.*?)(?:#else[^\n]*\n(.*?))?#endif[^\n]*\n',
        lambda m: (m.group(2) or '').strip() + '\n', src, flags=re.DOTALL)
    src = re.sub(r'#define SUPERIMPOSE [01]\n', '', src)
    open(fpath, 'w').write(src)
    print('Resolved:', fn)
PYSHADER

  mkdir -p ${INSTALL}/usr/bin
  cp ${PKG_DIR}/scripts/startopenmsx.sh ${INSTALL}/usr/bin/startopenmsx.sh
  chmod +x ${INSTALL}/usr/bin/startopenmsx.sh

  mkdir -p ${INSTALL}/usr/config/emuelec/configs/openmsx/gptk
  cp ${PKG_DIR}/config/openmsx.gptk \
    ${INSTALL}/usr/config/emuelec/configs/openmsx/gptk/openmsx.gptk

  for d in share/machines share/extensions share/scripts share/skins persistent savestates; do
    mkdir -p ${INSTALL}/usr/config/emuelec/configs/openmsx/${d}
  done

  mkdir -p ${INSTALL}/usr/config/emuelec/configs/openmsx/libs
  for lib in libGLX.so.0 libGLdispatch.so.0; do
    if [ -f "${sysroot}/usr/lib/${lib}" ]; then
      cp "${sysroot}/usr/lib/${lib}" \
        "${INSTALL}/usr/config/emuelec/configs/openmsx/libs/${lib}"
    fi
  done
}