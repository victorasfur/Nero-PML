"""Controle de volume via teclas de mídia do Windows (ctypes puro, sem
dependências extras nem COM/pycaw — evita os problemas de instalação
que essas bibliotecas costumam ter em versões diferentes do Windows)."""

import ctypes

VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
KEYEVENTF_EXTENDEDKEY = 0x1
KEYEVENTF_KEYUP = 0x2


def _press_key(vk_code: int, times: int = 1) -> None:
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def increase_volume(steps: int = 2) -> bool:
    try:
        _press_key(VK_VOLUME_UP, steps)
        return True
    except (AttributeError, OSError) as e:
        print(f"[ERRO] Não foi possível ajustar o volume: {e}")
        return False


def decrease_volume(steps: int = 2) -> bool:
    try:
        _press_key(VK_VOLUME_DOWN, steps)
        return True
    except (AttributeError, OSError) as e:
        print(f"[ERRO] Não foi possível ajustar o volume: {e}")
        return False
