# Amiberry GUI crash on EmuELEC when using the hotkey

## Summary

Starting with the EmuELEC package update to Amiberry commit `ecef2fd19f61e9360869eb9d5ebe1ad4c5019c14` (tagged upstream as v7.7), pressing the Amiberry hotkey to open the GUI on Amlogic devices aborts with the log message:

```
INFO: Creating Amiberry GUI window...
Unable to create window: mali-fbdev: Can't create EGL window surface
```

The failure is reproducible on platforms that rely on the `mali-fbdev` SDL2 video backend (used on EmuELEC's Amlogic builds). In Amiberry v5.5 the same workflow completed successfully.

## Root cause

The SDL2 backend that EmuELEC ships for `mali-fbdev` supports only a single EGL window surface. When a second SDL window is requested, `SDL_EGL_CreateSurface` fails and SDL returns the error "Can't create EGL window surface". The backend explicitly sets the `SDL_WINDOW_OPENGL` flag on every new window and aborts when the surface allocation fails, which matches the crash observed when Amiberry 7.7 tries to spawn a dedicated GUI window.

The package bump introduced in EmuELEC commit `e9b20dbc70dd94addd5c7e6eb7b48cc7c1628bbc` updated Amiberry from the previously working commit `fc0645c51ce095f3f46c4faa70f9afab71d49526` (v5.5) to `ecef2fd19f61e9360869eb9d5ebe1ad4c5019c14`. Upstream Amiberry started creating an additional GUI window in that range, triggering the `mali-fbdev` limitation and leading to the regression.

## Recommendation

Reverting to the last known good upstream commit (`fc0645c51ce095f3f46c4faa70f9afab71d49526`) or patching Amiberry so that the GUI reuses the existing window on `mali-fbdev` devices avoids the crash until the SDL driver gains multi-window support. Alternatively, Amiberry could guard the new GUI path behind a runtime check that falls back to the legacy behaviour when `SDL_VIDEODRIVER` is `mali-fbdev`.
