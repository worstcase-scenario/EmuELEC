# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024-present EmuELEC (https://github.com/EmuELEC/EmuELEC)

PKG_NAME="lightspark"
PKG_VERSION="master"
PKG_ARCH="aarch64"
PKG_LICENSE="LGPL"
PKG_SITE="https://github.com/lightspark/lightspark"
PKG_URL="${PKG_SITE}/archive/refs/heads/master.tar.gz"
PKG_DEPENDS_TARGET="toolchain SDL2 ffmpeg glew cairo pango curl zlib libjpeg-turbo \
                    fontconfig pcre2 xz rtmpdump SDL2_mixer"
PKG_LONGDESC="Lightspark - Open Source Flash Player (SWF standalone)"
PKG_TOOLCHAIN="cmake"

PKG_CMAKE_OPTS_TARGET="
  -DCMAKE_BUILD_TYPE=Release
  -DCOMPILE_LIGHTSPARK=ON
  -DCOMPILE_TIGHTSPARK=OFF
  -DCOMPILE_NPAPI_PLUGIN=OFF
  -DCOMPILE_PPAPI_PLUGIN=OFF
  -DENABLE_GLES2=ON
  -DENABLE_LLVM=OFF
  -DENABLE_TEST_RUNNER=OFF
  -DENABLE_MEMORY_USAGE_PROFILING=OFF
  -DOPENGL_INCLUDE_DIR=${SYSROOT_PREFIX}/usr/include
  -DCMAKE_INSTALL_PREFIX=/usr
"

pre_configure_target() {
  python3 - "${PKG_BUILD}/src/platforms/engineutils.cpp" << 'PYEOF'
import sys, os

fname = sys.argv[1]
with open(fname, "r") as f:
    src = f.read()

count = 0

# Fix 1: create softcursor.h
cursor_header = os.path.join(os.path.dirname(fname), "softcursor.h")
with open(cursor_header, "w") as f:
    f.write(
'#pragma once\n'
'#include <SDL2/SDL.h>\n'
'#include <GLES3/gl3.h>\n'
'#include <stdio.h>\n'
'static GLuint _cur_prog=0, _cur_vbo=0, _cur_vao=0;\n'
'static GLint  _cur_pos=-1;\n'
'static bool _cur_failed=false;\n'
'static void drawSoftwareCursor(SDL_Window* w)\n'
'{\n'
'    if (_cur_failed) return;\n'
'    if (_cur_prog == 0) {\n'
'        const char* vsh = "#version 300 es\\nin vec2 p;\\nvoid main(){gl_Position=vec4(p,0.0,1.0);}\\n";\n'
'        const char* fsh = "#version 300 es\\nprecision mediump float;\\nout vec4 col;\\nvoid main(){col=vec4(1.0,1.0,1.0,1.0);}\\n";\n'
'        GLuint vs=glCreateShader(GL_VERTEX_SHADER);\n'
'        glShaderSource(vs,1,&vsh,0); glCompileShader(vs);\n'
'        GLint ok=0; glGetShaderiv(vs,GL_COMPILE_STATUS,&ok);\n'
'        if(!ok){ char buf[256]; glGetShaderInfoLog(vs,256,0,buf); fprintf(stderr,"CURSOR VS: %s\\n",buf); _cur_failed=true; return; }\n'
'        GLuint fs=glCreateShader(GL_FRAGMENT_SHADER);\n'
'        glShaderSource(fs,1,&fsh,0); glCompileShader(fs);\n'
'        glGetShaderiv(fs,GL_COMPILE_STATUS,&ok);\n'
'        if(!ok){ char buf[256]; glGetShaderInfoLog(fs,256,0,buf); fprintf(stderr,"CURSOR FS: %s\\n",buf); _cur_failed=true; return; }\n'
'        _cur_prog=glCreateProgram();\n'
'        glAttachShader(_cur_prog,vs); glAttachShader(_cur_prog,fs);\n'
'        glLinkProgram(_cur_prog);\n'
'        glGetProgramiv(_cur_prog,GL_LINK_STATUS,&ok);\n'
'        if(!ok){ char buf[256]; glGetProgramInfoLog(_cur_prog,256,0,buf); fprintf(stderr,"CURSOR LINK: %s\\n",buf); _cur_failed=true; return; }\n'
'        glDeleteShader(vs); glDeleteShader(fs);\n'
'        _cur_pos=glGetAttribLocation(_cur_prog,"p");\n'
'        glGenVertexArrays(1,&_cur_vao);\n'
'        glGenBuffers(1,&_cur_vbo);\n'
'    }\n'
'    int mx,my,ww,wh;\n'
'    SDL_GetMouseState(&mx,&my);\n'
'    SDL_GetWindowSize(w,&ww,&wh);\n'
'    float cx=(float)mx/ww*2.0f-1.0f;\n'
'    float cy=1.0f-(float)my/wh*2.0f;\n'
'    float sx=0.025f;\n'
'    float sy=sx*(float)ww/(float)wh;\n'
'    float v[]={cx,cy, cx+sx,cy-sy*0.5f, cx+sx*0.45f,cy-sy*1.3f};\n'
'    GLint prevProg,prevVao,prevVbo;\n'
'    glGetIntegerv(GL_CURRENT_PROGRAM,&prevProg);\n'
'    glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&prevVao);\n'
'    glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&prevVbo);\n'
'    glUseProgram(_cur_prog);\n'
'    glBindVertexArray(_cur_vao);\n'
'    glBindBuffer(GL_ARRAY_BUFFER,_cur_vbo);\n'
'    glBufferData(GL_ARRAY_BUFFER,sizeof(v),v,GL_DYNAMIC_DRAW);\n'
'    glEnableVertexAttribArray(_cur_pos);\n'
'    glVertexAttribPointer(_cur_pos,2,GL_FLOAT,GL_FALSE,0,0);\n'
'    glDisable(GL_BLEND);\n'
'    glDisable(GL_DEPTH_TEST);\n'
'    glDrawArrays(GL_TRIANGLES,0,3);\n'
'    glBindBuffer(GL_ARRAY_BUFFER,prevVbo);\n'
'    glBindVertexArray(prevVao);\n'
'    glUseProgram(prevProg);\n'
'}\n'
    )
count += 1

# Fix 2: include softcursor.h and call drawSoftwareCursor in DoSwapBuffers
old = ("void EngineData::DoSwapBuffers()\n"
    "{\n"
    "\tuint32_t err;\n"
    "\tif (getGLError(err))\n"
    "\t\tLOG(LOG_ERROR,\"swapbuffers:\"<<widget<<\" \"<<err);\n"
    "\tSDL_GL_SwapWindow(widget);\n"
    "}")
new = ("#include \"softcursor.h\"\n"
    "void EngineData::DoSwapBuffers()\n"
    "{\n"
    "\tuint32_t err;\n"
    "\tif (getGLError(err))\n"
    "\t\tLOG(LOG_ERROR,\"swapbuffers:\"<<widget<<\" \"<<err);\n"
    "#if defined(ENABLE_GLES2) || defined(ENABLE_GLES3)\n"
    "\tdrawSoftwareCursor(widget);\n"
    "#endif\n"
    "\tSDL_GL_SwapWindow(widget);\n"
    "}")
if old in src:
    src = src.replace(old, new, 1); count += 1
else:
    print("WARNING: Fix 2 not found"); sys.exit(1)

with open(fname, "w") as f:
    f.write(src)

print("Lightspark patches applied: {}/2 fixes OK".format(count))
PYEOF
}

makeinstall_target() {
  local RELEASE_DIR="${PKG_BUILD}/.${TARGET_NAME}/aarch64/Release"

  mkdir -p ${INSTALL}/usr/bin
  cp -v "${RELEASE_DIR}/bin/lightspark" ${INSTALL}/usr/bin/
  chmod +x ${INSTALL}/usr/bin/lightspark

  mkdir -p ${INSTALL}/usr/lib
  cp -av "${RELEASE_DIR}/lib/." ${INSTALL}/usr/lib/

  cp -v ${PKG_DIR}/scripts/lightsparkstart.sh ${INSTALL}/usr/bin/lightsparkstart.sh
  chmod +x ${INSTALL}/usr/bin/lightsparkstart.sh

  if [ -f "${PKG_DIR}/config/lightspark.gptk" ]; then
    mkdir -p ${INSTALL}/usr/config/emuelec/configs/lightspark/gptk
    cp -f "${PKG_DIR}/config/lightspark.gptk" \
      "${INSTALL}/usr/config/emuelec/configs/lightspark/gptk/lightspark.gptk"
  fi
}