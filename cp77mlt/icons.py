"""Game icon for the launch button.

The icon is read from the user's own Cyberpunk2077.exe (the same icon Explorer
and Steam show), so no game artwork has to ship with the tool. If extraction
fails, the bundled icons/game_icon.png from v2 is used.
"""
from __future__ import annotations

import base64
import hashlib
import os
import struct
import sys
import zlib

SIZE = 96


def _png(width: int, height: int, rgba: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    stride = width * 4
    raw = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def extract_exe_icon(exe: str, size: int = SIZE) -> bytes | None:
    """Return PNG bytes of the exe's main icon at `size` px, or None."""
    if sys.platform != "win32" or not os.path.isfile(exe):
        return None
    import ctypes
    from ctypes import wintypes

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    HICON = wintypes.HANDLE
    user32.PrivateExtractIconsW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                            ctypes.POINTER(HICON), ctypes.POINTER(wintypes.UINT),
                                            wintypes.UINT, wintypes.UINT]
    user32.PrivateExtractIconsW.restype = wintypes.UINT
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, HICON, ctypes.c_int, ctypes.c_int,
                                  wintypes.UINT, wintypes.HBRUSH, wintypes.UINT]
    user32.DestroyIcon.argtypes = [HICON]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    hicon, icon_id = HICON(), wintypes.UINT()
    if user32.PrivateExtractIconsW(exe, 0, size, size, ctypes.byref(hicon), ctypes.byref(icon_id), 1, 0) < 1 \
            or not hicon.value:
        return None
    screen = user32.GetDC(None)
    mem = gdi32.CreateCompatibleDC(screen)
    bmi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    try:
        if not hbmp or not bits.value:
            return None
        old = gdi32.SelectObject(mem, hbmp)
        user32.DrawIconEx(mem, 0, 0, hicon, size, size, 0, None, 0x0003)  # DI_NORMAL
        bgra = ctypes.string_at(bits.value, size * size * 4)
        gdi32.SelectObject(mem, old)
    finally:
        if hbmp:
            gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(None, screen)
        user32.DestroyIcon(hicon)
    px = bytearray(bgra)
    px[0::4], px[2::4] = px[2::4], px[0::4]           # BGRA -> RGBA
    if not any(px[3::4]):                             # legacy icon without alpha channel
        px[3::4] = b"\xff" * (size * size)
    if not any(px[i] for i in range(len(px)) if i % 4 != 3):
        return None                                   # nothing was drawn
    return _png(size, size, bytes(px))


def bundled_data_uri(name: str) -> str | None:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        with open(os.path.join(base, "icons", name), "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return None


def _bundled_fallback() -> bytes | None:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p = os.path.join(base, "icons", "game_icon.png")
    try:
        with open(p, "rb") as f:
            return f.read()
    except OSError:
        return None


def game_icon_data_uri(exe: str, cache_path: str) -> str | None:
    tag = hashlib.md5(exe.lower().encode()).hexdigest()[:10] if exe else "none"
    cached = f"{os.path.splitext(cache_path)[0]}_{tag}.png"
    data = None
    if os.path.isfile(cached):
        with open(cached, "rb") as f:
            data = f.read()
    if not data:
        try:
            data = extract_exe_icon(exe)
        except Exception:
            data = None
        if data:
            try:
                with open(cached, "wb") as f:
                    f.write(data)
            except OSError:
                pass
    data = data or _bundled_fallback()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii") if data else None
