"""Ações de YouTube via navegador padrão.

Só abrimos URLs (home ou página de resultados de busca). Não controlamos a
reprodução: o navegador não pode ser "mandado dar play" de forma confiável a
partir daqui, então PLAY_MUSIC e YOUTUBE_SEARCH ambos abrem a busca — e a
assistente NUNCA afirma que "começou a tocar", só que encontrou/abriu.
"""

import webbrowser
from urllib.parse import quote_plus

HOME_URL = "https://www.youtube.com"


def search_url(query: str) -> str:
    return f"{HOME_URL}/results?search_query={quote_plus((query or '').strip())}"


def open_youtube() -> None:
    webbrowser.open_new_tab(HOME_URL)


def search_youtube(query: str) -> None:
    webbrowser.open_new_tab(search_url(query))
