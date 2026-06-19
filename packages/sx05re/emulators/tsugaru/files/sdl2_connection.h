// SPDX-License-Identifier: BSD-3-Clause
// SDL2 Outside_World implementation for EmuELEC/aarch64 (no X11/GLX).
// Drop-in replacement for FsSimpleWindowConnection.
// Does NOT include fssimplewindow.h or any GL headers.
#pragma once

// Suppress GL header inclusion from fssimplewindow.h if it gets pulled in
#define FSSIMPLEWINDOW_DONT_INCLUDE_OPENGL_HEADERS

#include "outside_world.h"
#include "discimg.h"
#include <SDL2/SDL.h>
#include <vector>
#include <mutex>
#include <atomic>
#include <thread>

#include <queue>

class SDL2Connection : public Outside_World
{
public:
    struct KeyEvent  { unsigned int key; bool release; };
    struct MouseEvent{ int lb=-1, rb=-1, x=0, y=0; bool rel=false; };

    std::queue<KeyEvent>   pendingKeys;
    std::queue<MouseEvent> pendingMouse;
    std::mutex             inputLock;
public:
    // ------------------------------------------------------------------ Window
    class WindowConnection : public WindowInterface
    {
    public:
        SDL_Window   *win  = nullptr;

        std::mutex          imgLock;
        TownsRender::ImageCopy pendingImg;
        bool                imgDirty = false;

        SDL2Connection *parent = nullptr;

        std::thread         renderThread;
        std::atomic<bool>   running{false};

        void Start()   override;
        void Stop()    override;
        void Interval() override;
        void Render(bool swapBuffers) override;
        void UpdateImage(TownsRender::ImageCopy &img) override;
        void Communicate(Outside_World *) override;
    };

    // ------------------------------------------------------------------ Sound
    class SoundConnection : public Sound
    {
    public:
        SDL_AudioDeviceID audioDev = 0;

        // CDDA — GetWave() returns raw signed 16-bit stereo PCM as bytes
        std::vector<uint8_t> cddaWave;
        size_t               cddaBytePos = 0;
        bool                 cddaLoop = false;
        float                cddaVolL = 1.f, cddaVolR = 1.f;
        DiscImage::MinSecFrm cddaFrom;
        std::mutex           cddaLock;

        // FM/PCM
        std::vector<uint8_t> fmpcmWave;
        size_t               fmpcmPos = 0;
        std::mutex           fmpcmLock;

        // Beep
        std::vector<uint8_t> beepWave;
        int                  beepRate = 44100;
        size_t               beepPos  = 0;
        std::mutex           beepLock;

        static void AudioCallback(void *userdata, uint8_t *stream, int len);

        void Start()   override;
        void Stop()    override;
        void Polling() override {}

        void CDDAPlay(const DiscImage &discImg,
                      DiscImage::MinSecFrm from, DiscImage::MinSecFrm to,
                      bool repeat, unsigned int, unsigned int) override;
        void CDDASetVolume(float l, float r) override;
        void CDDAStop()    override;
        void CDDAPause()   override;
        void CDDAResume()  override;
        bool CDDAIsPlaying() override;
        DiscImage::MinSecFrm CDDACurrentPosition() override;

        void FMPCMPlay(std::vector<uint8_t> &wave) override;
        void FMPCMPlayStop() override;
        bool FMPCMChannelPlaying() override;

        void BeepPlay(int samplingRate, std::vector<uint8_t> &wave) override;
        void BeepPlayStop() override;
        bool BeepChannelPlaying() const override;

    private:
        bool cddaPlaying  = false;
        bool cddaPaused   = false;
    };

    // ------------------------------------------------------------------ Input
    unsigned int sdlToTowns[SDL_NUM_SCANCODES] = {};

    SDL2Connection();
    ~SDL2Connection();

    std::string GetProgramResourceDirectory() const override;
    void Start()  override;
    void Stop()   override;
    void DevicePolling(class FMTownsCommon &towns) override;
    bool ImageNeedsFlip() override { return false; }
    void SetKeyboardLayout(unsigned int) override {}

    WindowInterface *CreateWindowInterface() const override;
    void DeleteWindowInterface(WindowInterface *) const override;
    Sound *CreateSound() const override;
    void DeleteSound(Sound *) const override;

private:
    void BuildKeyMap();
};