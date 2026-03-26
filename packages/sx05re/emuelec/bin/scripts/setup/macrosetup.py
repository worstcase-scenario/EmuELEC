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
_NAV  = {e.ABS_X:("left","right"), e.ABS_Y:("up","down"), e.ABS_RX:("left","right"),
         e.ABS_RY:("up","down"), e.ABS_HAT0X:("left","right"), e.ABS_HAT0Y:("up","down")}
_B2K  = {e.BTN_DPAD_UP:e.KEY_UP, e.BTN_DPAD_DOWN:e.KEY_DOWN, e.BTN_DPAD_LEFT:e.KEY_LEFT,
         e.BTN_DPAD_RIGHT:e.KEY_RIGHT, e.BTN_SOUTH:e.KEY_Z, e.BTN_EAST:e.KEY_X,
         e.BTN_NORTH:e.KEY_A, e.BTN_WEST:e.KEY_S, e.BTN_TL:e.KEY_Q, e.BTN_TR:e.KEY_W,
         e.BTN_TL2:e.KEY_E, e.BTN_TR2:e.KEY_R}
_A2K  = {e.ABS_X:{1:e.KEY_RIGHT,-1:e.KEY_LEFT}, e.ABS_Y:{1:e.KEY_DOWN,-1:e.KEY_UP},
         e.ABS_RX:{1:e.KEY_D,-1:e.KEY_A}, e.ABS_RY:{1:e.KEY_S,-1:e.KEY_W},
         e.ABS_Z:{1:e.KEY_E,-1:None}, e.ABS_RZ:{1:e.KEY_R,-1:None},
         e.ABS_HAT0X:{1:e.KEY_RIGHT,-1:e.KEY_LEFT}, e.ABS_HAT0Y:{1:e.KEY_DOWN,-1:e.KEY_UP}}

if hasattr(sys.stdout,"reconfigure"):
    try: sys.stdout.reconfigure(line_buffering=True)
    except: pass

def _nr(dev,c,v):
    k=(dev.path,c)
    if k not in _AC:
        try: i=dev.absinfo(c); _AC[k]=((i.min+i.max)/2,max((i.max-i.min)/2,1.))
        except: _AC[k]=(0.,32767.)
    a,b=_AC[k]; return (v-a)/b

def _dp(dev,c,v):
    n=_nr(dev,c,v); p=_NAV.get(c)
    return p[n>0] if p and abs(n)>=DZ else None

def _at(dev,c,v): return c in(e.ABS_Z,e.ABS_RZ) and _nr(dev,c,v)>DZ
def _aa(dev,c,v): return abs(_nr(dev,c,v))>=DZ

def _nodes(pref=None):
    ds=[]
    for p in list_devices():
        try: ds.append(InputDevice(p))
        except: pass
    a=next((d for d in ds if d.path==pref),None) if pref else None
    if not a: a=next((d for d in ds if any(b in d.capabilities().get(e.EV_KEY,[]) for b in _GB)),None)
    if not a: return []
    base=a.name.rstrip(" 0123456789")
    return [a]+[d for d in ds if d.path!=a.path and d.name.startswith(base)
                and (d.capabilities().get(e.EV_KEY) or d.capabilities().get(e.EV_ABS))]

def wait(pref=None):
    print("\nWaiting for controller...")
    while True:
        ns=_nodes(pref)
        if ns: print(f"  {ns[0].name}"); return ns
        time.sleep(1)

def revt(devs,timeout=None):
    fm={d.fd:d for d in devs}; dl=time.monotonic()+timeout if timeout else None
    while True:
        r=max(0,dl-time.monotonic()) if dl else None
        if dl and r==0: return
        rd,_,_=select.select(fm,[],[],r)
        if not rd: return
        for fd in rd:
            try:
                for ev in fm[fd].read(): yield fm[fd],ev
            except: pass

def cls(): print("\033[2J\033[H",end="",flush=True)

_BA={e.BTN_DPAD_UP:"up",e.BTN_DPAD_DOWN:"down",e.BTN_DPAD_LEFT:"left",
     e.BTN_DPAD_RIGHT:"right",e.BTN_SOUTH:"ok",e.BTN_EAST:"cancel",e.BTN_WEST:"erase"}

def nav(dev,ev,aa):
    if ev.type==e.EV_KEY and ev.value==1: return _BA.get(ev.code)
    if ev.type==e.EV_ABS:
        was,now=aa.get(ev.code,False),_aa(dev,ev.code,ev.value)
        aa[ev.code]=now
        if now and not was: return "ok" if _at(dev,ev.code,ev.value) else _dp(dev,ev.code,ev.value)
    return None

def menu(devs,title,opts,cancel=False):
    idx,aa=0,{}
    while True:
        cls(); print(f"{title}\nStick: navigate  A: confirm"+("  B: cancel" if cancel else "")+"\n")
        for i,o in enumerate(opts): print(f"{'->.' if i==idx else '   '}{o}")
        for dev,ev in revt(devs):
            act=nav(dev,ev,aa)
            if act=="down": idx=(idx+1)%len(opts); break
            if act=="up":   idx=(idx-1)%len(opts); break
            if act=="ok":   return idx
            if act=="cancel" and cancel: return None

def lcfg():
    if not os.path.exists(CFG): return {"macros":[]}
    with open(CFG) as f: d=json.load(f)
    if "macros" not in d:
        d={"device_path":d.get("device_path"),"macros":[{"name":"DEFAULT","trigger_code":d.get("trigger_code"),
           "macro_events":[{"type":"key","code":k} for k in d.get("macro_keys",[])]}]}
    for m in d.get("macros",[]):
        if "macro_keys" in m and "macro_events" not in m:
            m["macro_events"]=[{"type":"key","code":k} for k in m.pop("macro_keys")]
    return d

def scfg(d):
    os.makedirs(os.path.dirname(CFG),exist_ok=True)
    with open(CFG,"w") as f: json.dump(d,f,indent=2)
    print(f"Saved.")

def _cy(n,p,s):
    try: i=ALPHA.index(n[p])
    except: i=0
    n[p]=ALPHA[(i+s)%len(ALPHA)]

def enter_name(devs,dflt,L=16):
    nm=list(dflt.upper()[:L].ljust(L)); pos,aa=0,{}
    while True:
        cls(); print("Name  (Stick: move/change  A: ok  B: cancel  Y: erase)\n")
        print("".join(f"[{c}]" if i==pos else f" {c} " for i,c in enumerate(nm)))
        for dev,ev in revt(devs):
            act=nav(dev,ev,aa)
            if act=="right": pos=min(pos+1,L-1); break
            if act=="left":  pos=max(pos-1,0); break
            if act=="up":    _cy(nm,pos,+1); break
            if act=="down":  _cy(nm,pos,-1); break
            if act=="erase": nm[pos]=" "; break
            if act=="ok":    return "".join(nm).strip() or dflt.upper()
            if act=="cancel": return None

def rec_trig(devs):
    print("\nPress trigger button...")
    for _,ev in revt(devs):
        if ev.type==e.EV_KEY and ev.value==1 and ev.code!=e.BTN_MODE:
            print(f"Trigger: {ev.code}"); time.sleep(0.5); return ev.code

def rec_seq(devs,trig):
    print("\nRecord inputs. Wait 3 s to finish.")
    evts,last,prev=[],time.monotonic(),{}
    while True:
        for dev,ev in revt(devs,timeout=0.2):
            if ev.type==e.EV_KEY and ev.value==1 and ev.code!=trig:
                k=_B2K.get(ev.code)
                if k: evts.append({"type":"key","code":k}); last=time.monotonic(); print(f"  btn {ev.code}")
            elif ev.type==e.EV_ABS:
                n=_nr(dev,ev.code,ev.value)
                if abs(n)<DZ: prev.pop(ev.code,None)
                else:
                    p=prev.get(ev.code)
                    if p is None or (p>0)!=(n>0):
                        k=_A2K.get(ev.code,{}).get(1 if n>0 else -1)
                        if k:
                            evts.append({"type":"axis","code":ev.code,"value":ev.value,"mapped_key":k})
                            last=time.monotonic(); print(f"  axis {ev.code}{'+' if n>0 else '-'}")
                    prev[ev.code]=n
        if time.monotonic()-last>3: break
    if not evts: print("Nothing recorded."); return None
    print(f"Recorded {len(evts)}."); return evts

def main():
    cfg=lcfg(); devs=wait(cfg.get("device_path")); macros=cfg.setdefault("macros",[])
    opts=[f"Overwrite: {m['name']}" for m in macros]+["Create new macro"]
    sel=menu(devs,"Macro Setup",opts,cancel=True)
    if sel is None: return
    new=sel==len(macros)
    name=enter_name(devs,f"MACRO {len(macros)+1}") if new else macros[sel]["name"]
    if name is None: return
    trig=rec_trig(devs); evts=rec_seq(devs,trig)
    if not evts: return
    m={"name":name,"trigger_code":trig,"macro_events":evts}
    if new: macros.append(m)
    else: macros[sel]=m
    cfg["device_path"]=next((d for d in devs if d.capabilities().get(e.EV_KEY)),devs[0]).path
    scfg(cfg); print(f"'{name}' saved.")

if __name__=="__main__": main()
