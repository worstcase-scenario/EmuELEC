// SPDX-License-Identifier: BSD-3-Clause
// SDL2 Outside_World implementation for EmuELEC/aarch64 (no X11/GLX).

#define FSSIMPLEWINDOW_DONT_INCLUDE_OPENGL_HEADERS
#include "sdl2_connection.h"
#include "towns.h"
#include "townsdef.h"
#include <cstring>
#include <algorithm>

// ============================================================ key map

void SDL2Connection::BuildKeyMap()
{
    memset(sdlToTowns, 0, sizeof(sdlToTowns));
    sdlToTowns[SDL_SCANCODE_A]=TOWNS_JISKEY_A; sdlToTowns[SDL_SCANCODE_B]=TOWNS_JISKEY_B;
    sdlToTowns[SDL_SCANCODE_C]=TOWNS_JISKEY_C; sdlToTowns[SDL_SCANCODE_D]=TOWNS_JISKEY_D;
    sdlToTowns[SDL_SCANCODE_E]=TOWNS_JISKEY_E; sdlToTowns[SDL_SCANCODE_F]=TOWNS_JISKEY_F;
    sdlToTowns[SDL_SCANCODE_G]=TOWNS_JISKEY_G; sdlToTowns[SDL_SCANCODE_H]=TOWNS_JISKEY_H;
    sdlToTowns[SDL_SCANCODE_I]=TOWNS_JISKEY_I; sdlToTowns[SDL_SCANCODE_J]=TOWNS_JISKEY_J;
    sdlToTowns[SDL_SCANCODE_K]=TOWNS_JISKEY_K; sdlToTowns[SDL_SCANCODE_L]=TOWNS_JISKEY_L;
    sdlToTowns[SDL_SCANCODE_M]=TOWNS_JISKEY_M; sdlToTowns[SDL_SCANCODE_N]=TOWNS_JISKEY_N;
    sdlToTowns[SDL_SCANCODE_O]=TOWNS_JISKEY_O; sdlToTowns[SDL_SCANCODE_P]=TOWNS_JISKEY_P;
    sdlToTowns[SDL_SCANCODE_Q]=TOWNS_JISKEY_Q; sdlToTowns[SDL_SCANCODE_R]=TOWNS_JISKEY_R;
    sdlToTowns[SDL_SCANCODE_S]=TOWNS_JISKEY_S; sdlToTowns[SDL_SCANCODE_T]=TOWNS_JISKEY_T;
    sdlToTowns[SDL_SCANCODE_U]=TOWNS_JISKEY_U; sdlToTowns[SDL_SCANCODE_V]=TOWNS_JISKEY_V;
    sdlToTowns[SDL_SCANCODE_W]=TOWNS_JISKEY_W; sdlToTowns[SDL_SCANCODE_X]=TOWNS_JISKEY_X;
    sdlToTowns[SDL_SCANCODE_Y]=TOWNS_JISKEY_Y; sdlToTowns[SDL_SCANCODE_Z]=TOWNS_JISKEY_Z;
    sdlToTowns[SDL_SCANCODE_1]=TOWNS_JISKEY_1; sdlToTowns[SDL_SCANCODE_2]=TOWNS_JISKEY_2;
    sdlToTowns[SDL_SCANCODE_3]=TOWNS_JISKEY_3; sdlToTowns[SDL_SCANCODE_4]=TOWNS_JISKEY_4;
    sdlToTowns[SDL_SCANCODE_5]=TOWNS_JISKEY_5; sdlToTowns[SDL_SCANCODE_6]=TOWNS_JISKEY_6;
    sdlToTowns[SDL_SCANCODE_7]=TOWNS_JISKEY_7; sdlToTowns[SDL_SCANCODE_8]=TOWNS_JISKEY_8;
    sdlToTowns[SDL_SCANCODE_9]=TOWNS_JISKEY_9; sdlToTowns[SDL_SCANCODE_0]=TOWNS_JISKEY_0;
    sdlToTowns[SDL_SCANCODE_ESCAPE]    = TOWNS_JISKEY_ESC;
    sdlToTowns[SDL_SCANCODE_RETURN]    = TOWNS_JISKEY_RETURN;
    sdlToTowns[SDL_SCANCODE_SPACE]     = TOWNS_JISKEY_SPACE;
    sdlToTowns[SDL_SCANCODE_BACKSPACE] = TOWNS_JISKEY_BACKSPACE;
    sdlToTowns[SDL_SCANCODE_TAB]       = TOWNS_JISKEY_TAB;
    sdlToTowns[SDL_SCANCODE_LSHIFT]    = TOWNS_JISKEY_SHIFT;
    sdlToTowns[SDL_SCANCODE_RSHIFT]    = TOWNS_JISKEY_SHIFT;
    sdlToTowns[SDL_SCANCODE_LCTRL]     = TOWNS_JISKEY_CTRL;
    sdlToTowns[SDL_SCANCODE_RCTRL]     = TOWNS_JISKEY_CTRL;
    sdlToTowns[SDL_SCANCODE_LALT]      = TOWNS_JISKEY_ALT;
    sdlToTowns[SDL_SCANCODE_RALT]      = TOWNS_JISKEY_ALT;
    sdlToTowns[SDL_SCANCODE_UP]        = TOWNS_JISKEY_UP;
    sdlToTowns[SDL_SCANCODE_DOWN]      = TOWNS_JISKEY_DOWN;
    sdlToTowns[SDL_SCANCODE_LEFT]      = TOWNS_JISKEY_LEFT;
    sdlToTowns[SDL_SCANCODE_RIGHT]     = TOWNS_JISKEY_RIGHT;
    sdlToTowns[SDL_SCANCODE_INSERT]    = TOWNS_JISKEY_INSERT;
    sdlToTowns[SDL_SCANCODE_DELETE]    = TOWNS_JISKEY_DELETE;
    sdlToTowns[SDL_SCANCODE_HOME]      = TOWNS_JISKEY_HOME;
    sdlToTowns[SDL_SCANCODE_END]       = TOWNS_JISKEY_NEXT;
    sdlToTowns[SDL_SCANCODE_PAGEUP]    = TOWNS_JISKEY_PREV;
    sdlToTowns[SDL_SCANCODE_PAGEDOWN]  = TOWNS_JISKEY_NEXT;
    sdlToTowns[SDL_SCANCODE_F1] =TOWNS_JISKEY_PF01; sdlToTowns[SDL_SCANCODE_F2] =TOWNS_JISKEY_PF02;
    sdlToTowns[SDL_SCANCODE_F3] =TOWNS_JISKEY_PF03; sdlToTowns[SDL_SCANCODE_F4] =TOWNS_JISKEY_PF04;
    sdlToTowns[SDL_SCANCODE_F5] =TOWNS_JISKEY_PF05; sdlToTowns[SDL_SCANCODE_F6] =TOWNS_JISKEY_PF06;
    sdlToTowns[SDL_SCANCODE_F7] =TOWNS_JISKEY_PF07; sdlToTowns[SDL_SCANCODE_F8] =TOWNS_JISKEY_PF08;
    sdlToTowns[SDL_SCANCODE_F9] =TOWNS_JISKEY_PF09; sdlToTowns[SDL_SCANCODE_F10]=TOWNS_JISKEY_PF10;
    sdlToTowns[SDL_SCANCODE_F11]=TOWNS_JISKEY_PF11; sdlToTowns[SDL_SCANCODE_F12]=TOWNS_JISKEY_PF12;
    sdlToTowns[SDL_SCANCODE_MINUS]        = TOWNS_JISKEY_MINUS;
    sdlToTowns[SDL_SCANCODE_EQUALS]       = TOWNS_JISKEY_HAT;
    sdlToTowns[SDL_SCANCODE_BACKSLASH]    = TOWNS_JISKEY_BACKSLASH;
    sdlToTowns[SDL_SCANCODE_LEFTBRACKET]  = TOWNS_JISKEY_AT;
    sdlToTowns[SDL_SCANCODE_RIGHTBRACKET] = TOWNS_JISKEY_LEFT_SQ_BRACKET;
    sdlToTowns[SDL_SCANCODE_SEMICOLON]    = TOWNS_JISKEY_SEMICOLON;
    sdlToTowns[SDL_SCANCODE_APOSTROPHE]   = TOWNS_JISKEY_COLON;
    sdlToTowns[SDL_SCANCODE_COMMA]        = TOWNS_JISKEY_COMMA;
    sdlToTowns[SDL_SCANCODE_PERIOD]       = TOWNS_JISKEY_DOT;
    sdlToTowns[SDL_SCANCODE_SLASH]        = TOWNS_JISKEY_SLASH;
    sdlToTowns[SDL_SCANCODE_CAPSLOCK]     = TOWNS_JISKEY_CAPS;
    sdlToTowns[SDL_SCANCODE_KP_0]=TOWNS_JISKEY_NUM_0; sdlToTowns[SDL_SCANCODE_KP_1]=TOWNS_JISKEY_NUM_1;
    sdlToTowns[SDL_SCANCODE_KP_2]=TOWNS_JISKEY_NUM_2; sdlToTowns[SDL_SCANCODE_KP_3]=TOWNS_JISKEY_NUM_3;
    sdlToTowns[SDL_SCANCODE_KP_4]=TOWNS_JISKEY_NUM_4; sdlToTowns[SDL_SCANCODE_KP_5]=TOWNS_JISKEY_NUM_5;
    sdlToTowns[SDL_SCANCODE_KP_6]=TOWNS_JISKEY_NUM_6; sdlToTowns[SDL_SCANCODE_KP_7]=TOWNS_JISKEY_NUM_7;
    sdlToTowns[SDL_SCANCODE_KP_8]=TOWNS_JISKEY_NUM_8; sdlToTowns[SDL_SCANCODE_KP_9]=TOWNS_JISKEY_NUM_9;
    sdlToTowns[SDL_SCANCODE_KP_PLUS]    = TOWNS_JISKEY_NUM_PLUS;
    sdlToTowns[SDL_SCANCODE_KP_MINUS]   = TOWNS_JISKEY_NUM_MINUS;
    sdlToTowns[SDL_SCANCODE_KP_MULTIPLY]= TOWNS_JISKEY_NUM_STAR;
    sdlToTowns[SDL_SCANCODE_KP_DIVIDE]  = TOWNS_JISKEY_NUM_SLASH;
    sdlToTowns[SDL_SCANCODE_KP_ENTER]   = TOWNS_JISKEY_NUM_RETURN;
    sdlToTowns[SDL_SCANCODE_KP_PERIOD]  = TOWNS_JISKEY_NUM_DOT;
    sdlToTowns[SDL_SCANCODE_KP_EQUALS]  = TOWNS_JISKEY_NUM_EQUAL;
}

// ============================================================ SDL2Connection

SDL2Connection::SDL2Connection()  { BuildKeyMap(); }
SDL2Connection::~SDL2Connection() {}

std::string SDL2Connection::GetProgramResourceDirectory() const { return ""; }
void SDL2Connection::Start()  {}
void SDL2Connection::Stop()   {}

void SDL2Connection::DevicePolling(FMTownsCommon &towns)
{
    if (this->closeWindow)
        towns.var.powerOff = true;

    // Drain input queues filled by the render thread
    std::lock_guard<std::mutex> lk(inputLock);
    while (!pendingKeys.empty()) {
        auto e = pendingKeys.front(); pendingKeys.pop();
        ProcessInkey(towns, e.release ? (e.key | 0x80) : e.key);
    }
    while (!pendingMouse.empty()) {
        auto e = pendingMouse.front(); pendingMouse.pop();
        if (e.rel)
            ProcessMouseDifferential(towns, e.lb, 0, e.rb, e.x, e.y, 0, 0);
        else
            ProcessMouse(towns, e.lb, 0, e.rb, e.x, e.y);
    }
}

Outside_World::WindowInterface *SDL2Connection::CreateWindowInterface() const
{
    auto *w = new WindowConnection;
    w->parent = const_cast<SDL2Connection *>(this);
    return w;
}
void SDL2Connection::DeleteWindowInterface(WindowInterface *w) const { delete w; }
Outside_World::Sound *SDL2Connection::CreateSound() const { return new SoundConnection; }
void SDL2Connection::DeleteSound(Sound *s) const { delete s; }

// ============================================================ WindowConnection

void SDL2Connection::WindowConnection::Start()
{
    // All SDL video/render operations must happen on the same thread (EGL context
    // is thread-local on Mali). Start the render thread and do SDL_Init there.
    running = true;
    renderThread = std::thread([this]() {
        SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK);
        SDL_JoystickEventState(SDL_ENABLE);
        for (int i = 0; i < SDL_NumJoysticks(); i++)
            SDL_JoystickOpen(i);

        win = SDL_CreateWindow("Tsugaru",
            SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
            640, 480,
            SDL_WINDOW_FULLSCREEN_DESKTOP | SDL_WINDOW_SHOWN);
        if (!win) {
            fprintf(stderr, "SDL_CreateWindow failed: %s\n", SDL_GetError());
            running = false;
            return;
        }
        fprintf(stderr, "SDL2 window created OK, driver: %s\n",
                SDL_GetCurrentVideoDriver());

        while (running) {
            Interval();
            Communicate(parent);
            Render(true);
            SDL_Delay(16);
        }

        SDL_DestroyWindow(win); win = nullptr;
        SDL_Quit();
    });
}

void SDL2Connection::WindowConnection::Stop()
{
    running = false;
    if (renderThread.joinable())
        renderThread.join();
}

void SDL2Connection::WindowConnection::UpdateImage(TownsRender::ImageCopy &img)
{
    static bool logged = false;
    if (!logged) {
        logged = true;
        fprintf(stderr, "UpdateImage: %dx%d rgba_bytes=%zu\n",
                img.wid, img.hei, img.rgba.size());
    }
    std::lock_guard<std::mutex> lk(imgLock);
    pendingImg = std::move(img);
    imgDirty   = true;
}

void SDL2Connection::WindowConnection::Render(bool swapBuffers)
{
    if (!win) return;

    TownsRender::ImageCopy local;
    bool dirty = false;
    {
        std::lock_guard<std::mutex> lk(imgLock);
        if (imgDirty) {
            local    = std::move(pendingImg);
            imgDirty = false;
            dirty    = true;
        }
    }

    if (dirty && local.wid > 0 && local.hei > 0 && !local.rgba.empty()) {
        static bool pixelLogged = false;
        if (!pixelLogged) {
            pixelLogged = true; // only log once
            bool hasColor = false;
            for (size_t i = 0; i + 3 < local.rgba.size(); i += 4) {
                if (local.rgba[i] || local.rgba[i+1] || local.rgba[i+2]) {
                    fprintf(stderr, "First non-black pixel at byte %zu: R=%d G=%d B=%d A=%d\n",
                            i, local.rgba[i], local.rgba[i+1], local.rgba[i+2], local.rgba[i+3]);
                    hasColor = true;
                    break;
                }
            }
            if (!hasColor)
                fprintf(stderr, "First frame: all pixels black. Will check CRTC via CUI.\n");
        }

        SDL_Surface *ws = SDL_GetWindowSurface(win);
        if (ws) {
            SDL_Surface *src = SDL_CreateRGBSurfaceFrom(
                (void *)local.rgba.data(),
                (int)local.wid, (int)local.hei,
                32, (int)local.wid * 4,
                0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000);
            if (src) {
                // Disable alpha blending so alpha=0 pixels are not treated as transparent
                SDL_SetSurfaceBlendMode(src, SDL_BLENDMODE_NONE);
                SDL_BlitScaled(src, nullptr, ws, nullptr);
                SDL_FreeSurface(src);
            }
        }
    }

    if (swapBuffers && win) {
        // DEBUG: draw a red 100x100 square in the corner to verify display output works
        SDL_Surface *ws2 = SDL_GetWindowSurface(win);
        if (ws2) {
            static int testFrame = 0;
            if (testFrame++ < 300) { // show for 5 seconds
                SDL_Rect r = {0, 0, 100, 100};
                SDL_FillRect(ws2, &r, SDL_MapRGB(ws2->format, 255, 0, 0));
            }
        }
        SDL_UpdateWindowSurface(win);
    }
}

void SDL2Connection::WindowConnection::Interval()
{
    // BaseInterval() processes the VRAM copy set by SendNewImage() from the VM thread,
    // renders it via TownsRender, and stores the result in winThr.mostRecentImage.
    BaseInterval();

    // If a new frame was rendered, upload it to the SDL2 texture
    if (winThr.newImageRendered) {
        winThr.newImageRendered = false;
        UpdateImage(winThr.mostRecentImage);
    }
}

void SDL2Connection::WindowConnection::Communicate(Outside_World *ow)
{
    if (!ow) return;
    auto *conn = static_cast<SDL2Connection *>(ow);

    SDL_Event ev;
    while (SDL_PollEvent(&ev))
    {
        switch (ev.type)
        {
        case SDL_QUIT:
            ow->closeWindow = true;
            break;
        case SDL_KEYDOWN:
        {
            auto sc = ev.key.keysym.scancode;
            if (sc == SDL_SCANCODE_F12) {
                bool grabbed = (SDL_GetRelativeMouseMode() == SDL_TRUE);
                SDL_SetRelativeMouseMode(grabbed ? SDL_FALSE : SDL_TRUE);
                break;
            }
            if (sc < SDL_NUM_SCANCODES && conn->sdlToTowns[sc]) {
                std::lock_guard<std::mutex> lk(conn->inputLock);
                conn->pendingKeys.push({conn->sdlToTowns[sc], false});
            }
            break;
        }
        case SDL_KEYUP:
        {
            auto sc = ev.key.keysym.scancode;
            if (sc < SDL_NUM_SCANCODES && conn->sdlToTowns[sc]) {
                std::lock_guard<std::mutex> lk(conn->inputLock);
                conn->pendingKeys.push({conn->sdlToTowns[sc], true});
            }
            break;
        }
        case SDL_MOUSEBUTTONDOWN:
        case SDL_MOUSEBUTTONUP:
        {
            bool down = (ev.type == SDL_MOUSEBUTTONDOWN);
            SDL2Connection::MouseEvent me;
            me.lb = (ev.button.button == SDL_BUTTON_LEFT)  ? (down?1:0) : -1;
            me.rb = (ev.button.button == SDL_BUTTON_RIGHT) ? (down?1:0) : -1;
            SDL_GetMouseState(&me.x, &me.y); me.rel = false;
            std::lock_guard<std::mutex> lk(conn->inputLock);
            conn->pendingMouse.push(me);
            break;
        }
        case SDL_MOUSEMOTION:
        {
            SDL2Connection::MouseEvent me;
            int btns = SDL_GetMouseState(nullptr, nullptr);
            me.lb = (btns & SDL_BUTTON(1)) ? 1 : 0;
            me.rb = (btns & SDL_BUTTON(3)) ? 1 : 0;
            me.rel = (SDL_GetRelativeMouseMode() == SDL_TRUE);
            me.x = me.rel ? ev.motion.xrel : ev.motion.x;
            me.y = me.rel ? ev.motion.yrel : ev.motion.y;
            std::lock_guard<std::mutex> lk(conn->inputLock);
            conn->pendingMouse.push(me);
            break;
        }
        case SDL_JOYBUTTONDOWN:
        case SDL_JOYBUTTONUP:
        {
            unsigned int port = (unsigned int)ev.jbutton.which;
            if (port < TOWNS_NUM_GAMEPORTS) {
                bool down = (ev.type == SDL_JOYBUTTONDOWN);
                if (ev.jbutton.button == 0) {
                    if (down) conn->gamePort[port] &= ~0x10u;
                    else      conn->gamePort[port] |=  0x10u;
                } else if (ev.jbutton.button == 1) {
                    if (down) conn->gamePort[port] &= ~0x20u;
                    else      conn->gamePort[port] |=  0x20u;
                }
            }
            break;
        }
        case SDL_JOYAXISMOTION:
        {
            unsigned int port = (unsigned int)ev.jaxis.which;
            if (port < TOWNS_NUM_GAMEPORTS) {
                int val = ev.jaxis.value;
                if (ev.jaxis.axis == 0) {
                    conn->gamePort[port] |=  0x0Cu;
                    if (val < -8000) conn->gamePort[port] &= ~0x04u;
                    if (val >  8000) conn->gamePort[port] &= ~0x08u;
                } else if (ev.jaxis.axis == 1) {
                    conn->gamePort[port] |=  0x03u;
                    if (val < -8000) conn->gamePort[port] &= ~0x01u;
                    if (val >  8000) conn->gamePort[port] &= ~0x02u;
                }
            }
            break;
        }
        }
    }
    if (closeWindow)
        ow->closeWindow = true;
}

// ============================================================ SoundConnection

void SDL2Connection::SoundConnection::AudioCallback(void *userdata, uint8_t *stream, int len)
{
    auto *self = static_cast<SoundConnection *>(userdata);
    memset(stream, 0, len);
    int samples = len / 2;
    auto *out = reinterpret_cast<int16_t *>(stream);

    // CDDA: raw bytes from GetWave() are signed 16-bit stereo little-endian
    {
        std::lock_guard<std::mutex> lk(self->cddaLock);
        if (self->cddaPlaying && !self->cddaPaused && !self->cddaWave.empty()) {
            for (int i = 0; i < samples; i++) {
                if (self->cddaBytePos + 1 >= self->cddaWave.size()) {
                    if (self->cddaLoop) self->cddaBytePos = 0;
                    else { self->cddaPlaying = false; break; }
                }
                // cddaWave is raw bytes; read as little-endian int16
                int16_t sample = (int16_t)(self->cddaWave[self->cddaBytePos] |
                                           (self->cddaWave[self->cddaBytePos+1] << 8));
                self->cddaBytePos += 2;
                float vol = (i & 1) ? self->cddaVolR : self->cddaVolL;
                int32_t v = (int32_t)((float)sample * vol);
                out[i] = (int16_t)std::max(-32768, std::min(32767, (int32_t)out[i] + v));
            }
        }
    }
    // FMPCM: unsigned 8-bit mono → stereo
    {
        std::lock_guard<std::mutex> lk(self->fmpcmLock);
        if (!self->fmpcmWave.empty() && self->fmpcmPos < self->fmpcmWave.size()) {
            for (int i = 0; i < samples; i += 2) {
                if (self->fmpcmPos >= self->fmpcmWave.size()) break;
                int16_t v = (int16_t)((self->fmpcmWave[self->fmpcmPos++] - 128) * 256);
                out[i]   = (int16_t)std::max(-32768, std::min(32767, (int32_t)out[i]   + v));
                out[i+1] = (int16_t)std::max(-32768, std::min(32767, (int32_t)out[i+1] + v));
            }
        }
    }
    // Beep
    {
        std::lock_guard<std::mutex> lk(self->beepLock);
        if (!self->beepWave.empty() && self->beepPos < self->beepWave.size()) {
            for (int i = 0; i < samples; i += 2) {
                if (self->beepPos >= self->beepWave.size()) break;
                int16_t v = (int16_t)((self->beepWave[self->beepPos++] - 128) * 256);
                out[i]   = (int16_t)std::max(-32768, std::min(32767, (int32_t)out[i]   + v));
                out[i+1] = (int16_t)std::max(-32768, std::min(32767, (int32_t)out[i+1] + v));
            }
        }
    }
}

void SDL2Connection::SoundConnection::Start()
{
    SDL_Init(SDL_INIT_AUDIO);
    SDL_AudioSpec want{}, have{};
    want.freq     = 44100;
    want.format   = AUDIO_S16SYS;
    want.channels = 2;
    want.samples  = 1024;
    want.callback = AudioCallback;
    want.userdata = this;
    audioDev = SDL_OpenAudioDevice(nullptr, 0, &want, &have, 0);
    if (audioDev) SDL_PauseAudioDevice(audioDev, 0);
}

void SDL2Connection::SoundConnection::Stop()
{
    if (audioDev) { SDL_CloseAudioDevice(audioDev); audioDev = 0; }
}

void SDL2Connection::SoundConnection::CDDAPlay(
    const DiscImage &discImg,
    DiscImage::MinSecFrm from, DiscImage::MinSecFrm to,
    bool repeat, unsigned int, unsigned int)
{
    // GetWave returns raw signed 16-bit stereo PCM as bytes
    auto wave = discImg.GetWave(from, to);
    std::lock_guard<std::mutex> lk(cddaLock);
    cddaWave     = std::move(wave);
    cddaBytePos  = 0;
    cddaLoop     = repeat;
    cddaPlaying  = true;
    cddaPaused   = false;
    cddaFrom     = from;
}

void SDL2Connection::SoundConnection::CDDASetVolume(float l, float r)
{
    std::lock_guard<std::mutex> lk(cddaLock);
    cddaVolL = l / 256.f;
    cddaVolR = r / 256.f;
}

void SDL2Connection::SoundConnection::CDDAStop()
{
    std::lock_guard<std::mutex> lk(cddaLock);
    cddaPlaying = false; cddaBytePos = 0;
}
void SDL2Connection::SoundConnection::CDDAPause()
{
    std::lock_guard<std::mutex> lk(cddaLock); cddaPaused = true;
}
void SDL2Connection::SoundConnection::CDDAResume()
{
    std::lock_guard<std::mutex> lk(cddaLock); cddaPaused = false;
}
bool SDL2Connection::SoundConnection::CDDAIsPlaying()
{
    std::lock_guard<std::mutex> lk(cddaLock);
    return cddaPlaying && !cddaPaused;
}
DiscImage::MinSecFrm SDL2Connection::SoundConnection::CDDACurrentPosition()
{
    std::lock_guard<std::mutex> lk(cddaLock);
    // Each stereo int16 pair = 4 bytes; 44100 pairs/sec → 75 frames/HSG-sec
    size_t frames = cddaBytePos / 4;
    double secs   = (double)frames / 44100.0;
    unsigned long long hsg = cddaFrom.ToHSG() + (unsigned long long)(secs * 75.0);
    // FromHSG is an instance method, not static
    DiscImage::MinSecFrm pos;
    pos.FromHSG((unsigned int)hsg);
    return pos;
}

void SDL2Connection::SoundConnection::FMPCMPlay(std::vector<uint8_t> &wave)
{
    std::lock_guard<std::mutex> lk(fmpcmLock);
    fmpcmWave = wave; fmpcmPos = 0;
}
void SDL2Connection::SoundConnection::FMPCMPlayStop()
{
    std::lock_guard<std::mutex> lk(fmpcmLock); fmpcmPos = fmpcmWave.size();
}
bool SDL2Connection::SoundConnection::FMPCMChannelPlaying()
{
    std::lock_guard<std::mutex> lk(fmpcmLock);
    return fmpcmPos < fmpcmWave.size();
}

void SDL2Connection::SoundConnection::BeepPlay(int samplingRate, std::vector<uint8_t> &wave)
{
    std::lock_guard<std::mutex> lk(beepLock);
    beepWave = wave; beepRate = samplingRate; beepPos = 0;
}
void SDL2Connection::SoundConnection::BeepPlayStop()
{
    std::lock_guard<std::mutex> lk(beepLock); beepPos = beepWave.size();
}
bool SDL2Connection::SoundConnection::BeepChannelPlaying() const
{
    return beepPos < beepWave.size();
}