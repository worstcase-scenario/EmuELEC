#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)
import json, os, select, sys, time
from evdev import InputDevice, list_devices, ecodes as e, UInput

CFG  = "/storage/.config/emuelec/scripts/macro_config.json"
PID  = "/tmp/macrorun.pid"
LOG  = "/tmp/macrorun.log"
DZ   = 0.30
_AC  = {}
_GB  = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST]
_NAV = {e.ABS_X:("left","right"), e.ABS_Y:("up","down"), e.ABS_RX:("left","right"),
        e.ABS_RY:("up","down"), e.ABS_HAT0X:("left","right"), e.ABS_HAT0Y:("up","down")}
_KL  = {e.KEY_UP:"D↑",e.KEY_DOWN:"D↓",e.KEY_LEFT:"D<",e.KEY_RIGHT:"D>",
        e.KEY_Z:"A",e.KEY_X:"B",e.KEY_A:"X",e.KEY_S:"Y",
        e.KEY_Q:"L1",e.KEY_W:"R1",e.KEY_E:"L2",e.KEY_R:"R2"}
_AL  = {(e.ABS_X,1):"LS>",(e.ABS_X,-1):"LS<",(e.ABS_Y,1):"LS↓",(e.ABS_Y,-1):"LS↑",
        (e.ABS_RX,1):"RS>",(e.ABS_RX,-1):"RS<",(e.ABS_RY,1):"RS↓",(e.ABS_RY,-1):"RS↑",
        (e.ABS_Z,1):"L2",(e.ABS_RZ,1):"R2",
        (e.ABS_HAT0X,1):"D>",(e.ABS_HAT0X,-1):"D<",(e.ABS_HAT0Y,1):"D↓",(e.ABS_HAT0Y,-1):"D↑"}
_TL  = {e.BTN_SOUTH:"A",e.BTN_EAST:"B",e.BTN_NORTH:"X",e.BTN_WEST:"Y",
        e.BTN_TL:"L1",e.BTN_TR:"R1",e.BTN_TL2:"L2",e.BTN_TR2:"R2",
        e.BTN_THUMBL:"L3",e.BTN_THUMBR:"R3",e.BTN_START:"START",e.BTN_SELECT:"SELECT",
        e.BTN_MODE:"HOME",e.BTN_DPAD_UP:"D↑",e.BTN_DPAD_DOWN:"D↓",
        e.BTN_DPAD_LEFT:"D<",e.BTN_DPAD_RIGHT:"D>"}

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

_BA={e.BTN_DPAD_UP:"up",e.BTN_DPAD_DOWN:"down",e.BTN_SOUTH:"ok",e.BTN_EAST:"cancel"}

def nav(dev,ev,aa):
    if ev.type==e.EV_KEY and ev.value==1: return _BA.get(ev.code)
    if ev.type==e.EV_ABS:
        was,now=aa.get(ev.code,False),_aa(dev,ev.code,ev.value)
        aa[ev.code]=now
        if now and not was: return "ok" if _at(dev,ev.code,ev.value) else _dp(dev,ev.code,ev.value)
    return None

def lcfg():
    if not os.path.exists(CFG): print("No config. Run Macro Setup first."); sys.exit(1)
    with open(CFG) as f: d=json.load(f)
    if "macros" not in d:
        d={"device_path":d.get("device_path"),"macros":[{"name":"DEFAULT","trigger_code":d.get("trigger_code"),
           "macro_events":[{"type":"key","code":k} for k in d.get("macro_keys",[])]}]}
    for m in d.get("macros",[]):
        if "macro_keys" in m and "macro_events" not in m:
            m["macro_events"]=[{"type":"key","code":k} for k in m.pop("macro_keys")]
    d["macros"]=[m for m in d["macros"] if m.get("macro_events")]
    if not d["macros"]: print("No macros. Run Macro Setup first."); sys.exit(1)
    return d

def _tok(evts):
    out=[]
    for ev in evts:
        if ev["type"]=="key": out.append(_KL.get(ev["code"],f"k{ev['code']}"))
        elif ev["type"]=="axis":
            d=1 if ev.get("value",1)>0 else -1
            out.append(_AL.get((ev["code"],d),f"ax{ev['code']}"))
    return out

def _seq(toks,w=44):
    ls,cur=[],"  "
    for i,t in enumerate(toks):
        p=t if i==0 else "→"+t
        if len(cur)+len(p)>w and cur.strip(): ls.append(cur); cur="  "+t
        else: cur+=p
    if cur.strip(): ls.append(cur)
    return ls or ["  (empty)"]

def pick(devs,macros):
    idx,aa=0,{}
    while True:
        cls(); print("Macro Enabler  —  Stick: navigate  A: activate  B: cancel\n")
        for i,m in enumerate(macros):
            evts=m.get("macro_events",[])
            info=(f"{sum(1 for x in evts if x['type']=='key')}btn "
                  f"{sum(1 for x in evts if x['type']=='axis')}ax  "
                  f"[{_TL.get(m['trigger_code'],m['trigger_code'])}]")
            if i==idx:
                print(f"-> {m['name']}  {info}")
                for l in _seq(_tok(evts)): print(l)
                print()
            else: print(f"   {m['name']}  {info}")
        for dev,ev in revt(devs):
            act=nav(dev,ev,aa)
            if act=="down": idx=(idx+1)%len(macros); break
            if act=="up":   idx=(idx-1)%len(macros); break
            if act=="ok":   return idx
            if act=="cancel": sys.exit(0)

def _play(ui,evts,delay=0.05):
    for ev in evts:
        k=ev.get("code") if ev["type"]=="key" else ev.get("mapped_key")
        if not k: continue
        ui.write(e.EV_KEY,k,1); ui.syn(); time.sleep(delay); ui.write(e.EV_KEY,k,0); ui.syn()

def run_macro(dev,macro):
    trig,evts=macro["trigger_code"],macro["macro_events"]
    keys=({ev["code"] for ev in evts if ev["type"]=="key"}|
          {ev["mapped_key"] for ev in evts if ev["type"]=="axis" and ev.get("mapped_key")})
    if not keys: return
    ui=UInput({e.EV_KEY:list(keys)},name="Virtual-Macro",bustype=e.BUS_USB)
    pressed,done,t0=False,False,0.
    for ev in dev.read_loop():
        if ev.type==e.EV_KEY and ev.code==trig:
            if ev.value==1: pressed,done,t0=True,False,time.time()
            elif ev.value==0 and pressed:
                held,pressed=time.time()-t0,False
                if held>=3: ui.close(); return
                if not done: _play(ui,evts)
        if pressed and not done and time.time()-t0>=0.1: done=True; _play(ui,evts)

def running():
    try:
        with open(PID) as f: pid=int(f.read().strip())
        os.kill(pid,0); return True
    except: return False

def daemonize(dev_path,macro):
    try:
        if os.fork()>0: return 0
        os.setsid()
        if os.fork()>0: os._exit(0)
    except OSError: return 2
    try: sys.stdin.close()
    except: pass
    try: log=open(LOG,"ab",buffering=0)
    except: log=open("/dev/null","ab",buffering=0)
    for fd in(1,2):
        try: os.dup2(log.fileno(),fd)
        except: pass
    try:
        with open(PID,"w") as f: f.write(str(os.getpid()))
    except: pass
    try: run_macro(InputDevice(dev_path),macro)
    finally:
        try: os.remove(PID)
        except: pass
    os._exit(0)

def main():
    if running(): print("Already running."); return 0
    cfg=lcfg(); devs=wait(cfg.get("device_path"))
    macro=cfg["macros"][pick(devs,cfg["macros"])]
    btn=next((d for d in devs if d.capabilities().get(e.EV_KEY)),devs[0])
    return 0 if daemonize(btn.path,macro)==0 else 1

if __name__=="__main__": sys.exit(main())
