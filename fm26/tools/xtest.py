#!/usr/bin/env python3
"""Minimal XTest input helper (works with XWayland/X11 clients).

Commands:
  move X Y            move pointer to absolute X,Y in X11 screen coords
  click X Y [button]  move then click (button default 1)
  pos                 print current pointer position
  key KEYSYM          press+release a keysym (e.g. Return, Escape, Tab)
  type TEXT           type ASCII text
"""
import ctypes
import sys
import time

X11 = ctypes.CDLL("libX11.so.6")
XTST = ctypes.CDLL("libXtst.so.6")

X11.XOpenDisplay.restype = ctypes.c_void_p
X11.XOpenDisplay.argtypes = [ctypes.c_char_p]
X11.XFlush.argtypes = [ctypes.c_void_p]
X11.XStringToKeysym.restype = ctypes.c_ulong
X11.XStringToKeysym.argtypes = [ctypes.c_char_p]
X11.XKeysymToKeycode.restype = ctypes.c_ubyte
X11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
XTST.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
XTST.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
XTST.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]

_dpy = X11.XOpenDisplay(None)


def flush():
    X11.XFlush(_dpy)


def _query():
    X11.XDefaultScreen.argtypes = [ctypes.c_void_p]
    X11.XDefaultScreen.restype = ctypes.c_int
    X11.XRootWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    X11.XRootWindow.restype = ctypes.c_ulong
    root_win = X11.XRootWindow(_dpy, X11.XDefaultScreen(_dpy))
    X11.XQueryPointer.restype = ctypes.c_int
    X11.XQueryPointer.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_uint),
    ]
    r = ctypes.c_ulong()
    c = ctypes.c_ulong()
    rx = ctypes.c_int()
    ry = ctypes.c_int()
    wx = ctypes.c_int()
    wy = ctypes.c_int()
    m = ctypes.c_uint()
    X11.XQueryPointer(
        _dpy, root_win,
        ctypes.byref(r), ctypes.byref(c),
        ctypes.byref(rx), ctypes.byref(ry),
        ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(m),
    )
    return rx.value, ry.value


def move(x, y):
    for _ in range(12):
        cx, cy = _query()
        if abs(x - cx) <= 2 and abs(y - cy) <= 2:
            return
        XTST.XTestFakeMotionEvent(_dpy, -1, int(x), int(y), 0)
        flush()
        time.sleep(0.05)


def click(x, y, button=1):
    move(x, y)
    XTST.XTestFakeButtonEvent(_dpy, int(button), 1, 0)
    flush()
    time.sleep(0.06)
    XTST.XTestFakeButtonEvent(_dpy, int(button), 0, 0)
    flush()
    time.sleep(0.06)


def _keycode(keysym_name):
    ks = X11.XStringToKeysym(keysym_name.encode())
    if ks == 0:
        raise SystemExit(f"unknown keysym {keysym_name}")
    return X11.XKeysymToKeycode(_dpy, ks)


def key(keysym_name):
    kc = _keycode(keysym_name)
    XTST.XTestFakeKeyEvent(_dpy, kc, 1, 0)
    XTST.XTestFakeKeyEvent(_dpy, kc, 0, 0)
    flush()
    time.sleep(0.05)


SHIFT = None


def type_text(text):
    global SHIFT
    if SHIFT is None:
        SHIFT = _keycode("Shift_L")
    for ch in text:
        if ch.isalpha():
            name = ch if ch.islower() else ch
            ks = X11.XStringToKeysym(name.encode())
            kc = X11.XKeysymToKeycode(_dpy, ks)
            need_shift = ch.isupper()
        else:
            special = {
                " ": "space", ".": "period", ",": "comma", "-": "minus",
                "_": "underscore", "/": "slash", "@": "at",
            }
            name = special.get(ch, ch)
            ks = X11.XStringToKeysym(name.encode())
            if ks == 0:
                continue
            kc = X11.XKeysymToKeycode(_dpy, ks)
            need_shift = ch in "_@"
        if need_shift:
            XTST.XTestFakeKeyEvent(_dpy, SHIFT, 1, 0)
        XTST.XTestFakeKeyEvent(_dpy, kc, 1, 0)
        XTST.XTestFakeKeyEvent(_dpy, kc, 0, 0)
        if need_shift:
            XTST.XTestFakeKeyEvent(_dpy, SHIFT, 0, 0)
        flush()
        time.sleep(0.03)


def pos():
    X11.XDefaultScreen.restype = ctypes.c_int
    X11.XDefaultScreen.argtypes = [ctypes.c_void_p]
    X11.XRootWindow.restype = ctypes.c_ulong
    X11.XRootWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    root_win = X11.XRootWindow(_dpy, X11.XDefaultScreen(_dpy))
    X11.XQueryPointer.restype = ctypes.c_int
    X11.XQueryPointer.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_uint),
    ]
    root = ctypes.c_ulong()
    child = ctypes.c_ulong()
    rx = ctypes.c_int()
    ry = ctypes.c_int()
    wx = ctypes.c_int()
    wy = ctypes.c_int()
    mask = ctypes.c_uint()
    X11.XQueryPointer(
        _dpy, root_win,
        ctypes.byref(root), ctypes.byref(child),
        ctypes.byref(rx), ctypes.byref(ry),
        ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(mask),
    )
    print(rx.value, ry.value)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "move":
        move(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "click":
        btn = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        click(int(sys.argv[2]), int(sys.argv[3]), btn)
    elif cmd == "key":
        key(sys.argv[2])
    elif cmd == "type":
        type_text(sys.argv[2])
    elif cmd == "pos":
        pos()
