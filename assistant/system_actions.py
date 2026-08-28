"""Ações de sistema seguras: abrir sites e aplicativos.

REGRA DE SEGURANÇA (seções 14, 15 e 35 do pedido):
- A IA NUNCA fornece um caminho, URL ou comando. Ela devolve apenas uma
  INTENÇÃO (ex.: OPEN_VSCODE) e é ESTE módulo que resolve o alvo por uma
  tabela fixa (config.settings.WEB_TARGETS / VSCODE_CANDIDATES).
- Não há uso de subprocess/os.system/shell com string vinda de fora. Sites
  abrem pelo `webbrowser`; o VS Code abre por `os.startfile` num caminho de
  instalação conhecido.
"""

import os
import webbrowser
from typing import Optional

from config import settings


def open_web_target(key: str) -> bool:
    """Abre um site do allowlist `WEB_TARGETS`. `key` é uma CHAVE conhecida
    (ex.: "google"), nunca uma URL arbitrária."""
    url = settings.WEB_TARGETS.get((key or "").strip().lower())
    if not url:
        print(f"[ERRO] Alvo de site não permitido: {key!r}")
        return False
    try:
        webbrowser.open_new_tab(url)
        return True
    except Exception as e:  # noqa: BLE001 - queremos degradar com elegância
        print(f"[ERRO] Falha ao abrir {url}: {e}")
        return False


def open_browser() -> bool:
    return open_web_target("navegador")


def open_google() -> bool:
    return open_web_target("google")


def _resolve_vscode() -> Optional[str]:
    for candidate in settings.VSCODE_CANDIDATES:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def open_vscode() -> bool:
    path = _resolve_vscode()
    if not path:
        print("[ERRO] VS Code não encontrado nos caminhos de instalação conhecidos.")
        return False
    try:
        os.startfile(path)  # noqa: S606 - caminho fixo do allowlist, não vem de entrada
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao abrir o VS Code: {e}")
        return False
