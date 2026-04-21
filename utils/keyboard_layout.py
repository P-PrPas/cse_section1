import ctypes
import platform


IS_WINDOWS = platform.system().lower() == "windows"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    WM_INPUTLANGCHANGEREQUEST = 0x0050
    KLF_ACTIVATE = 0x00000001
    _LANGUAGE_MAP = {
        0x0409: "English",
        0x0411: "Thai",
    }


def _lang_id_from_hkl(hkl):
    return int(hkl) & 0xFFFF


def get_current_keyboard_language():
    if not IS_WINDOWS:
        return "Unknown"

    hkl = user32.GetKeyboardLayout(0)
    lang_id = _lang_id_from_hkl(hkl)
    return _LANGUAGE_MAP.get(lang_id, f"0x{lang_id:04X}")


def is_thai_keyboard():
    return get_current_keyboard_language() == "Thai"


def _load_keyboard_layout(locale_hex):
    if not IS_WINDOWS:
        return False

    hkl = user32.LoadKeyboardLayoutW(locale_hex, KLF_ACTIVATE)
    if not hkl:
        return False

    hwnd = user32.GetForegroundWindow()
    if hwnd:
        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, hkl)

    return bool(user32.ActivateKeyboardLayout(hkl, 0))


def set_keyboard_language(language_name):
    if not IS_WINDOWS:
        return False

    normalized = (language_name or "").strip().lower()
    if normalized in {"th", "thai", "thailand"}:
        return _load_keyboard_layout("00000411")
    if normalized in {"en", "eng", "english"}:
        return _load_keyboard_layout("00000409")
    return False


def toggle_keyboard_language():
    current = get_current_keyboard_language()
    target = "Thai" if current != "Thai" else "English"
    return set_keyboard_language(target)
