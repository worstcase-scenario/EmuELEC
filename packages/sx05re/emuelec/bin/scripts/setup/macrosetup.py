#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)

import json, os, select, sys, time
from evdev import InputDevice, list_devices, ecodes as e

CFG   = "/storage/.config/emuelec/scripts/macro_config.json"
ALPHA = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")
DZ    = 0.30
_AC   = {}
_GB   = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST]

_NAV = {e.ABS_X:("left","right"), e.ABS_Y:("up","down"), e.ABS_RX:("left","right"),
        e.ABS_RY:("up","down"), e.ABS_HAT0X:("left","right"), e.ABS_HAT0Y:("up","down")}

_TL = {e.BTN_SOUTH:"A", e.BTN_EAST:"B", e.BTN_NORTH:"X", e.BTN_WEST:"Y",
       e.BTN_TL:"L1", e.BTN_TR:"R1", e.BTN_TL2:"L2", e.BTN_TR2:"R2",
       e.BTN_THUMBL:"L3", e.BTN_THUMBR:"R3", e.BTN_START:"START", e.BTN_SELECT:"SELECT",
       e.BTN_MODE:"HOME", e.BTN_DPAD_UP:"D↑", e.BTN_DPAD_DOWN:"D↓",
       e.BTN_DPAD_LEFT:"D<", e.BTN_DPAD_RIGHT:"D>"}

_AX = {e.ABS_X:"X", e.ABS_Y:"Y", e.ABS_RX:"RX", e.ABS_RY:"RY",
       e.ABS_Z:"Z", e.ABS_RZ:"RZ", e.ABS_HAT0X:"HATX", e.ABS_HAT0Y:"HATY"}

_BA = {e.BTN_DPAD_UP:"up", e.BTN_DPAD_DOWN:"down", e.BTN_DPAD_LEFT:"left",
       e.BTN_DPAD_RIGHT:"right", e.BTN_SOUTH:"ok", e.BTN_EAST:"cancel", e.BTN_WEST:"erase"}

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

def menu(devs, title, opts, cancel=False, spacing=False):
    idx, aa, result = 0, {}, None
    while result is None:
        cls()
        print(title + "\n")
        for i, o in enumerate(opts):
            print(("-> " if i==idx else "   ") + o)
            if spacing: print()
        end_screen()
        redraw = False
        while not redraw and result is None:
            for dev, ev in revt(devs):
                act = nav(dev, ev, aa)
                if act == "down":              idx = (idx+1) % len(opts); redraw = True; break
                if act == "up":                idx = (idx-1) % len(opts); redraw = True; break
                if act == "ok":                result = idx; break
                if act == "cancel" and cancel: result = -1; break
    return None if result == -1 else result

def fmt_events(evts):
    parts = []
    for ev in evts:
        if ev["type"] == "key":
            parts.append(_TL.get(ev["code"], f"BTN_{ev['code']}"))
        elif ev["type"] == "axis":
            parts.append(_AX.get(ev["code"], f"AX{ev['code']}") + ("+" if ev.get("value",0)>0 else "-"))
    return ", ".join(parts)

def enter_name(devs, dflt, L=16):
    nm = list(dflt.upper()[:L].ljust(L))
    pos, aa, done = 0, {}, None
    while done is None:
        cls()
        print("Name\n")
        print("".join(f"[{c}]" if i==pos else f" {c} " for i, c in enumerate(nm)))
        end_screen()
        redraw = False
        while not redraw and done is None:
            for dev, ev in revt(devs):
                act = nav(dev, ev, aa)
                if act == "right":  pos = min(pos+1, L-1);                                  redraw = True; break
                if act == "left":   pos = max(pos-1, 0);                                    redraw = True; break
                if act == "up":     nm[pos] = ALPHA[(ALPHA.index(nm[pos])+1) % len(ALPHA)]; redraw = True; break
                if act == "down":   nm[pos] = ALPHA[(ALPHA.index(nm[pos])-1) % len(ALPHA)]; redraw = True; break
                if act == "erase":  nm[pos] = " ";                                          redraw = True; break
                if act == "ok":     done = "ok"; break
                if act == "cancel": return None
    return "".join(nm).strip() or dflt

def rec_trig(devs):
    print("\nPress trigger button...")
    while True:
        for _, ev in revt(devs):
            if ev.type==e.EV_KEY and ev.value==1:
                print(f"Trigger: {_TL.get(ev.code, str(ev.code))}")
                time.sleep(0.5); return ev.code

def rec_seq(devs, trig):
    print("\nRecording... wait 3s to finish\n")
    evts, last, prev_axis = [], time.monotonic(), {}
    while True:
        for dev, ev in revt(devs, 0.2):
            if ev.type==e.EV_KEY and ev.value==1 and ev.code!=trig:
                if ev.code in _TL:
                    print(f"  {_TL[ev.code]}")
                    evts.append({"type": "key", "code": ev.code})
                    last = time.monotonic()
            elif ev.type==e.EV_ABS:
                n = _nr(dev, ev.code, ev.value)
                if abs(n) < DZ:
                    prev_axis.pop(ev.code, None)
                elif ev.code in _AX:
                    prev = prev_axis.get(ev.code)
                    if prev is None or (prev>0) != (n>0):
                        label = _AX[ev.code] + ("+" if n>0 else "-")
                        print(f"  {label}")
                        evts.append({"type": "axis", "code": ev.code, "value": ev.value})
                        last = time.monotonic()
                    prev_axis[ev.code] = n
        if time.monotonic()-last > 3: break
    return evts if evts else None

def lcfg():
    if not os.path.exists(CFG): return {"macros": []}
    with open(CFG) as f: return json.load(f)

def scfg(d):
    os.makedirs(os.path.dirname(CFG), exist_ok=True)
    with open(CFG, "w") as f: json.dump(d, f, indent=2)

def main():
    cfg    = lcfg()
    devs   = wait(cfg.get("device_path"))
    macros = cfg.setdefault("macros", [])

    while True:
        opts = [f"Overwrite: {m['name']}  [{fmt_events(m.get('macro_events',[]))}]" for m in macros]
        opts += ["Create new macro"]
        if macros: opts += ["Delete a macro"]

        sel = menu(devs, "Macro Setup  —  A: select  B: cancel", opts, cancel=True, spacing=True)
        if sel is None: return

        if macros and sel == len(macros) + 1:
            del_sel = menu(devs, "Delete which macro?",
                           [f"{m['name']}  [{fmt_events(m.get('macro_events',[]))}]" for m in macros],
                           cancel=True, spacing=True)
            if del_sel is None: continue
            del macros[del_sel]
            cfg["device_path"] = devs[0].path
            scfg(cfg)
        else:
            new  = sel == len(macros)
            name = enter_name(devs, f"MACRO {len(macros)+1}") if new else macros[sel]["name"]
            if name is None: continue
            trig = rec_trig(devs)
            evts = rec_seq(devs, trig)
            if not evts: continue
            m = {"name": name, "trigger_code": trig, "macro_events": evts}
            if new: macros.append(m)
            else:   macros[sel] = m
            cfg["device_path"] = devs[0].path
            scfg(cfg)
            print("\nSaved.")
            return

if __name__ == "__main__": main()