"""macOS Accessibility permission helpers (ctypes; no extra pyobjc deps).

Accessibility is required for the global hotkey (event tap) and for pasting text
(synthetic Cmd-V). We surface the system prompt and can open the settings pane,
mirroring Willow's onboarding.
"""
import ctypes
import subprocess

ACCESSIBILITY_PANE = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

_APP_SERVICES = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
_CORE_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"


def is_trusted() -> bool:
    """True if this process already has Accessibility permission."""
    try:
        lib = ctypes.cdll.LoadLibrary(_APP_SERVICES)
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        return False


def prompt_accessibility() -> bool:
    """Register this app and show the system Accessibility prompt.

    Returns the current trust state. The prompt's button opens System Settings
    with the app already listed, ready to toggle on.
    """
    try:
        appsvc = ctypes.cdll.LoadLibrary(_APP_SERVICES)
        cf = ctypes.cdll.LoadLibrary(_CORE_FOUNDATION)

        cf.CFDictionaryCreate.restype = ctypes.c_void_p
        cf.CFDictionaryCreate.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_long,
            ctypes.c_void_p, ctypes.c_void_p,
        ]

        key = ctypes.c_void_p.in_dll(appsvc, "kAXTrustedCheckOptionPrompt")
        true_value = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")
        key_callbacks = ctypes.addressof(ctypes.c_char.in_dll(cf, "kCFTypeDictionaryKeyCallBacks"))
        value_callbacks = ctypes.addressof(ctypes.c_char.in_dll(cf, "kCFTypeDictionaryValueCallBacks"))

        keys = (ctypes.c_void_p * 1)(key)
        values = (ctypes.c_void_p * 1)(true_value)
        options = cf.CFDictionaryCreate(None, keys, values, 1, key_callbacks, value_callbacks)

        appsvc.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
        appsvc.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
        return bool(appsvc.AXIsProcessTrustedWithOptions(options))
    except Exception:
        return is_trusted()


def open_accessibility_settings() -> None:
    subprocess.run(["open", ACCESSIBILITY_PANE], check=False)
