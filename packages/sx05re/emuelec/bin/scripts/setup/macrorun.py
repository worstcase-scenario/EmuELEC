#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# THIS FILE HAS BEEN CREATED BY CLAUDE.AI
import json, os, select, sys, time, threading, queue
from evdev import InputDevice, list_devices, ecodes as e, UInput

CFG = "/storage/.config/emuelec/scripts/macro_config.json"
PID = "/tmp/macrorun.pid"
LOG = "/tmp/macrorun.log"
DZ  = 0.30
_AC = {}
_GB = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST]

_NAV = {e.ABS_X:("left","right"), e.ABS_Y:("up","down"), e.ABS_RX:("left","right"),
        e.ABS_RY:("up","down"), e.ABS_HAT0X:("left","right"), e.ABS_HAT0Y:("up","down")}

_TL = {e.BTN_SOUTH:"A", e.BTN_EAST:"B", e.BTN_NORTH:"X", e.BTN_WEST:"Y",
       e.BTN_TL:"L1", e.BTN_TR:"R1", e.BTN_TL2:"L2", e.BTN_TR2:"R2",
       e.BTN_THUMBL:"L3", e.BTN_THUMBR:"R3", e.BTN_START:"START", e.BTN_SELECT:"SELECT",
       e.BTN_MODE:"HOME", e.BTN_DPAD_UP:"D↑", e.BTN_DPAD_DOWN:"D↓",
       e.BTN_DPAD_LEFT:"D<", e.BTN_DPAD_RIGHT:"D>"}

_AX = {e.ABS_X:"X", e.ABS_Y:"Y", e.ABS_RX:"RX", e.ABS_RY:"RY",
       e.ABS_Z:"Z", e.ABS_RZ:"RZ", e.ABS_HAT0X:"HATX", e.ABS_HAT0Y:"HATY"}

# Button/axis → keyboard key mapping for UInput playback
# Emulators expect keyboard events, not virtual gamepad events
_B2K = {e.BTN_DPAD_UP:e.KEY_UP, e.BTN_DPAD_DOWN:e.KEY_DOWN,
        e.BTN_DPAD_LEFT:e.KEY_LEFT, e.BTN_DPAD_RIGHT:e.KEY_RIGHT,
        e.BTN_SOUTH:e.KEY_Z, e.BTN_EAST:e.KEY_X,
        e.BTN_NORTH:e.KEY_A, e.BTN_WEST:e.KEY_S,
        e.BTN_TL:e.KEY_Q, e.BTN_TR:e.KEY_W,
        e.BTN_TL2:e.KEY_E, e.BTN_TR2:e.KEY_R}

_A2K = {e.ABS_X:{1:e.KEY_RIGHT,-1:e.KEY_LEFT}, e.ABS_Y:{1:e.KEY_DOWN,-1:e.KEY_UP},
        e.ABS_RX:{1:e.KEY_D,-1:e.KEY_A}, e.ABS_RY:{1:e.KEY_S,-1:e.KEY_W},
        e.ABS_Z:{1:e.KEY_E}, e.ABS_RZ:{1:e.KEY_R},
        e.ABS_HAT0X:{1:e.KEY_RIGHT,-1:e.KEY_LEFT}, e.ABS_HAT0Y:{1:e.KEY_DOWN,-1:e.KEY_UP}}

_BA = {e.BTN_DPAD_UP:"up", e.BTN_DPAD_DOWN:"down", e.BTN_DPAD_LEFT:"left",
       e.BTN_DPAD_RIGHT:"right", e.BTN_SOUTH:"ok", e.BTN_EAST:"cancel"}

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(line_buffering=True)
    except: pass

def _nr(dev, c, v):
    k = (dev.path, c)
    if k not in _AC:
        try: i = dev.absinfo(c); _AC[k] = ((i.min+i.max)/2, max((i.max-i.min)/2, 1.))
        except: _AC[k] = (0., 32767.)
    a, b = _AC[k]; return (v-a)/b

def _dp(dev, c, v):
    n = _nr(dev, c, v); p = _NAV.get(c)
    return p[n>0] if p and abs(n)>=DZ else None

def _at(dev, c, v): return c in (e.ABS_Z, e.ABS_RZ) and _nr(dev, c, v) > DZ
def _aa(dev, c, v): return abs(_nr(dev, c, v)) >= DZ

def _nodes(pref=None):
    ds = []
    for p in list_devices():
        try: ds.append(InputDevice(p))
        except: pass
    a = next((d for d in ds if d.path==pref), None) if pref else None
    if not a: a = next((d for d in ds if any(b in d.capabilities().get(e.EV_KEY,[]) for b in _GB)), None)
    if not a: return []
    base = a.name.rstrip(" 0123456789")
    return [a] + [d for d in ds if d.path!=a.path and d.name.startswith(base)
                  and (d.capabilities().get(e.EV_KEY) or d.capabilities().get(e.EV_ABS))]

def wait(pref=None):
    ns = _nodes(pref)
    if not ns:
        print("\nWaiting for controller...")
        while not ns:
            time.sleep(1); ns = _nodes(pref)
        print(f"  {ns[0].name}")
    return ns

def revt(devs, timeout=0.1):
    fm = {d.fd:d for d in devs}
    result = []
    try:
        rd, _, _ = select.select(fm, [], [], timeout)
        for fd in rd:
            try:
                for ev in fm[fd].read(): result.append((fm[fd], ev))
            except: pass
    except: pass
    return result

def cls():        sys.stdout.write("\033[?25l\033[H\033[2J"); sys.stdout.flush()
def end_screen(): sys.stdout.write("\033[?25h");              sys.stdout.flush()

def nav(dev, ev, aa):
    if ev.type==e.EV_KEY and ev.value==1: return _BA.get(ev.code)
    if ev.type==e.EV_ABS:
        was, now = aa.get(ev.code, False), _aa(dev, ev.code, ev.value)
        aa[ev.code] = now
        if now and not was: return "ok" if _at(dev, ev.code, ev.value) else _dp(dev, ev.code, ev.value)
    return None

def fmt_macro(m):
    events = []
    for ev in m.get("macro_events", []):
        if ev["type"] == "key":
            events.append(_TL.get(ev["code"], f"BTN_{ev['code']}"))
        elif ev["type"] == "axis":
            val = ev.get("value", 0)
            events.append(_AX.get(ev["code"], f"AX{ev['code']}") + ("+" if val>0 else "-" if val<0 else ""))
    return _TL.get(m.get("trigger_code"), str(m.get("trigger_code"))), ", ".join(events)

def pick(devs, macros):
    idx, aa, result = 0, {}, None
    while result is None:
        cls()
        print("Macro Enabler  —  Stick: navigate  A: activate  B: cancel\n")
        for i, m in enumerate(macros):
            trig, evts = fmt_macro(m)
            p = "-> " if i==idx else "   "
            print(f"{p}{m.get('name','UNKNOWN').upper()}")
            print(f"{'':24}Trigger: [{trig}]")
            print(f"{'':24}Macro:   [{evts}]\n")
        end_screen()
        redraw = False
        while not redraw and result is None:
            for dev, ev in revt(devs):
                act = nav(dev, ev, aa)
                if act == "down":   idx = (idx+1) % len(macros); redraw = True; break
                if act == "up":     idx = (idx-1) % len(macros); redraw = True; break
                if act == "ok":     result = idx; break
                if act == "cancel": result = -1; break
    if result == -1: sys.exit(0)
    return result

def show_info(macro):
    trig, evts = fmt_macro(macro)
    cls()
    print("=" * 46)
    print("    M A C R O  ACTIVATED IN BACKGROUND")
    print("=" * 46)
    print(f"\nName   : {macro.get('name','UNKNOWN').upper()}")
    print(f"Trigger: [{trig}]")
    print(f"Macro  : [{evts}]")
    print("\nHold trigger 3 s at any time to stop it.")
    print("\nPress any button to continue...")
    end_screen()
    devs = _nodes()
    while True:
        for dev, ev in revt(devs):
            if ev.type in (e.EV_KEY, e.EV_ABS): return

def _make_ui(evts):
    keys = set()
    for ev in evts:
        if ev["type"] == "key":
            k = _B2K.get(ev["code"])
            if k: keys.add(k)
        elif ev["type"] == "axis":
            val = ev.get("value", 0)
            k = _A2K.get(ev["code"], {}).get(1 if val>0 else -1)
            if k: keys.add(k)
    if not keys: return None
    return UInput({e.EV_KEY: list(keys)}, name="Virtual-Macro", bustype=e.BUS_USB)

def _play(ui, evts, delay=0.05):
    if not ui: return
    for ev in evts:
        k = None
        if ev["type"] == "key":
            k = _B2K.get(ev["code"])
        elif ev["type"] == "axis":
            val = ev.get("value", 0)
            k = _A2K.get(ev["code"], {}).get(1 if val>0 else -1)
        if not k: continue
        ui.write(e.EV_KEY, k, 1); ui.syn(); time.sleep(delay)
        ui.write(e.EV_KEY, k, 0); ui.syn()

def run_macro(dev_paths, macro):
    trig, evts = macro["trigger_code"], macro["macro_events"]
    if not evts: return
    ui = _make_ui(evts)
    q = queue.Queue()

    def _reader(path):
        try:
            dev = InputDevice(path)
            for ev in dev.read_loop():
                q.put(ev)
        except: pass

    for p in dev_paths:
        threading.Thread(target=_reader, args=(p,), daemon=True).start()

    pressed, done, t0 = False, False, 0.
    while True:
        try:
            ev = q.get(timeout=0.05)
        except queue.Empty:
            if pressed and not done and time.time()-t0 >= 0.1:
                done = True; _play(ui, evts)
            continue
        if ev.type==e.EV_KEY and ev.code==trig:
            if ev.value==1: pressed, done, t0 = True, False, time.time()
            elif ev.value==0 and pressed:
                held, pressed = time.time()-t0, False
                if held >= 3: ui.close(); return
                if not done: _play(ui, evts)
        if pressed and not done and time.time()-t0 >= 0.1:
            done = True; _play(ui, evts)

def running():
    try:
        with open(PID) as f: pid = int(f.read().strip())
        os.kill(pid, 0); return True
    except: return False

def stop_running():
    try:
        with open(PID) as f: pid = int(f.read().strip())
        os.kill(pid, 15)
        time.sleep(0.2)
        if os.path.exists(PID): os.remove(PID)
    except: pass

def daemonize(dev_paths, macro):
    try:
        if os.fork() > 0: return 0
        os.setsid()
        if os.fork() > 0: os._exit(0)
    except OSError: return 2
    try: sys.stdin.close()
    except: pass
    try: log = open(LOG, "ab", buffering=0)
    except: log = open("/dev/null", "ab", buffering=0)
    for fd in (1, 2):
        try: os.dup2(log.fileno(), fd)
        except: pass
    try:
        with open(PID, "w") as f: f.write(str(os.getpid()))
    except: pass
    try: run_macro(dev_paths, macro)
    finally:
        try: os.remove(PID)
        except: pass
    os._exit(0)

def lcfg():
    if not os.path.exists(CFG): print("No config. Run Macro Setup first."); sys.exit(1)
    with open(CFG) as f: d = json.load(f)
    if "macros" not in d:
        d = {"device_path": d.get("device_path"), "macros": [{"name": "DEFAULT",
             "trigger_code": d.get("trigger_code"),
             "macro_events": [{"type": "key", "code": k} for k in d.get("macro_keys", [])]}]}
    for m in d.get("macros", []):
        if "macro_keys" in m and "macro_events" not in m:
            m["macro_events"] = [{"type": "key", "code": k} for k in m.pop("macro_keys")]
    d["macros"] = [m for m in d["macros"] if m.get("macro_events")]
    if not d["macros"]: print("No macros. Run Macro Setup first."); sys.exit(1)
    return d

def main():
    if running():
        cls()
        print("A macro is currently running in the background.")
        print("Press any button to stop it, or B to keep it.")
        end_screen()
        devs = _nodes()
        while True:
            for dev, ev in revt(devs):
                if ev.type == e.EV_KEY:
                    if ev.code == e.BTN_EAST: return 0
                    stop_running(); time.sleep(0.5); break
            else: continue
            break

    cfg = lcfg()
    devs = wait(cfg.get("device_path"))
    macro = cfg["macros"][pick(devs, cfg["macros"])]
    show_info(macro)
    return 0 if daemonize([d.path for d in devs], macro) == 0 else 1

if __name__ == "__main__": sys.exit(main())
