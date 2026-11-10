// SPDX-License-Identifier: GPL-2.0
// EGL shim for Steam Link on the Mali blob: Steam Link requests a desktop GL
// context for its video window, the blob only offers GLES. Bend the request to
// GLES2; the desktop GL calls themselves are translated by gl4es (libGL).
#define _GNU_SOURCE
#include <dlfcn.h>

typedef int EGLint;
typedef unsigned int EGLBoolean, EGLenum;

#define EGL_NONE                   0x3038
#define EGL_RENDERABLE_TYPE        0x3040
#define EGL_OPENGL_BIT             0x0008
#define EGL_OPENGL_ES2_BIT         0x0004
#define EGL_OPENGL_API             0x30A2
#define EGL_OPENGL_ES_API          0x30A0
#define EGL_CONTEXT_CLIENT_VERSION 0x3098

#define REAL(name) static __typeof__(name) *real; if (!real) real = dlsym(RTLD_NEXT, #name)

EGLBoolean eglChooseConfig(void *dpy, const EGLint *attr, void **cfg, EGLint n, EGLint *num)
{
	REAL(eglChooseConfig);
	EGLint a[64];
	int i = 0;
	for (; attr && attr[i] != EGL_NONE && i < 62; i += 2) {
		a[i] = attr[i];
		a[i + 1] = (attr[i] == EGL_RENDERABLE_TYPE && attr[i + 1] == EGL_OPENGL_BIT) ? EGL_OPENGL_ES2_BIT : attr[i + 1];
	}
	a[i] = EGL_NONE;
	return real(dpy, a, cfg, n, num);
}

EGLBoolean eglBindAPI(EGLenum api)
{
	REAL(eglBindAPI);
	return real(api == EGL_OPENGL_API ? EGL_OPENGL_ES_API : api);
}

void *eglCreateContext(void *dpy, void *cfg, void *share, const EGLint *attr)
{
	REAL(eglCreateContext);
	(void)attr; /* drop desktop GL version attributes */
	const EGLint a[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	return real(dpy, cfg, share, a);
}
