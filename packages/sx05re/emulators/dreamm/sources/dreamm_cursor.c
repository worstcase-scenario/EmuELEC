/* dreamm_cursor.c - software mouse pointer for SDL2/mali (EmuELEC, aarch64)
 *
 * Build (WSL, EmuELEC toolchain):
 *   $TC/bin/aarch64-libreelec-linux-gnu-gcc --sysroot=$TC/aarch64-libreelec-linux-gnu/sysroot \
 *       -shared -fPIC -O2 -o dreamm_cursor.so dreamm_cursor.c -ldl
 *
 * Usage:
 *   LD_PRELOAD=/emuelec/bin/dreamm_cursor.so ./dreamm -sdl -fullscreen
 *
 * Rationale: EmuELEC's SDL2 only provides the "mali" and "offscreen" video
 * drivers. The mali backend implements no cursor at all, so SDL_ShowCursor()
 * succeeds but draws nothing. This shim hooks SDL_RenderPresent and draws the
 * pointer onto the application's own renderer instead.
 *
 * Env:
 *   DREAMM_CURSOR_SCALE=3    pointer size (default 3)
 *   DREAMM_CURSOR_DEBUG=1    log mouse coordinates to stderr
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>

typedef struct { int x, y, w, h; } RECT;

static void  (*p_RenderPresent)(void*);
static uint32_t (*p_GetMouseState)(int*, int*);
static int   (*p_SetDrawColor)(void*, uint8_t, uint8_t, uint8_t, uint8_t);
static int   (*p_GetDrawColor)(void*, uint8_t*, uint8_t*, uint8_t*, uint8_t*);
static int   (*p_FillRect)(void*, const RECT*);
static int   (*p_WinToLogical)(void*, int, int, float*, float*);
static int   (*p_GetScale)(void*, float*, float*);
static int   (*p_SetBlend)(void*, int);
static int   (*p_GetBlend)(void*, int*);

/* 'o' = black outline, '#' = white fill, ' ' = transparent */
static const char *ARROW[] = {
    "o          ",
    "oo         ",
    "o#o        ",
    "o##o       ",
    "o###o      ",
    "o####o     ",
    "o#####o    ",
    "o######o   ",
    "o#######o  ",
    "o########o ",
    "o#####oooo ",
    "o##o##o    ",
    "o#o o##o   ",
    "oo   o##o  ",
    "o     o##o ",
    "       o#o ",
    "        oo ",
};
#define ARROW_H ((int)(sizeof(ARROW)/sizeof(ARROW[0])))

static void resolve(void)
{
    if (p_RenderPresent) return;
    p_RenderPresent = dlsym(RTLD_NEXT,    "SDL_RenderPresent");
    p_GetMouseState = dlsym(RTLD_DEFAULT, "SDL_GetMouseState");
    p_SetDrawColor  = dlsym(RTLD_DEFAULT, "SDL_SetRenderDrawColor");
    p_GetDrawColor  = dlsym(RTLD_DEFAULT, "SDL_GetRenderDrawColor");
    p_FillRect      = dlsym(RTLD_DEFAULT, "SDL_RenderFillRect");
    p_WinToLogical  = dlsym(RTLD_DEFAULT, "SDL_RenderWindowToLogical");
    p_GetScale      = dlsym(RTLD_DEFAULT, "SDL_RenderGetScale");
    p_SetBlend      = dlsym(RTLD_DEFAULT, "SDL_SetRenderDrawBlendMode");
    p_GetBlend      = dlsym(RTLD_DEFAULT, "SDL_GetRenderDrawBlendMode");
}

static void draw_cursor(void *r)
{
    int mx, my;
    float lx, ly;
    int s = 3;
    const char *e;

    if (!p_GetMouseState || !p_FillRect || !p_SetDrawColor) return;
    p_GetMouseState(&mx, &my);

    /* window coordinates -> renderer logical coordinates */
    if (p_WinToLogical) {
        p_WinToLogical(r, mx, my, &lx, &ly);
    } else if (p_GetScale) {
        float sx = 1.f, sy = 1.f;
        p_GetScale(r, &sx, &sy);
        lx = mx / (sx > 0 ? sx : 1.f);
        ly = my / (sy > 0 ? sy : 1.f);
    } else {
        lx = (float)mx; ly = (float)my;
    }

    if ((e = getenv("DREAMM_CURSOR_SCALE"))) { s = atoi(e); if (s < 1) s = 1; }
    if (getenv("DREAMM_CURSOR_DEBUG"))
        fprintf(stderr, "[cursor] win=%d,%d log=%.1f,%.1f\n", mx, my, lx, ly);

    /* save renderer state */
    uint8_t or_, og, ob, oa; int obm = 0;
    if (p_GetDrawColor) p_GetDrawColor(r, &or_, &og, &ob, &oa);
    if (p_GetBlend)     p_GetBlend(r, &obm);
    if (p_SetBlend)     p_SetBlend(r, 1);   /* SDL_BLENDMODE_BLEND */

    for (int pass = 0; pass < 2; pass++) {
        char want = pass ? '#' : 'o';
        if (pass) p_SetDrawColor(r, 255, 255, 255, 255);
        else      p_SetDrawColor(r, 0, 0, 0, 255);

        for (int row = 0; row < ARROW_H; row++) {
            const char *line = ARROW[row];
            for (int col = 0; line[col]; col++) {
                if (line[col] != want) continue;
                RECT q = { (int)lx + col * s, (int)ly + row * s, s, s };
                p_FillRect(r, &q);
            }
        }
    }

    /* restore renderer state */
    if (p_GetDrawColor) p_SetDrawColor(r, or_, og, ob, oa);
    if (p_SetBlend)     p_SetBlend(r, obm);
}

void SDL_RenderPresent(void *renderer)
{
    resolve();
    if (renderer) draw_cursor(renderer);
    if (p_RenderPresent) p_RenderPresent(renderer);
}

/* swallow attempts to hide the (non-existent) hardware cursor */
int SDL_ShowCursor(int toggle)
{
    (void)toggle;
    return 1;
}