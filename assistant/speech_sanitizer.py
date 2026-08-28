"""Deixa o texto pronto para ser FALADO pelo TTS: sem markdown, sem URLs
cruas, sem JSON. Evita que a assistente leia "asterisco asterisco", "abre
chaves", blocos de código etc. (seções 23 e 24 do pedido).

Fica num módulo próprio (sem dependências de áudio) para poder ser testado
sem importar o motor de voz.
"""

import re

_URL_RE = re.compile(r"https?://\S+")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)


def sanitize_for_speech(text: str) -> str:
    if not text:
        return ""
    text = text.strip()

    # Um retorno de classificação (JSON puro) NUNCA deve ser falado.
    if text.startswith("{") and text.endswith("}"):
        return "Certo."

    text = text.replace("```", " ")
    text = _MD_LINK_RE.sub(r"\1", text)        # [texto](url) -> texto
    text = _URL_RE.sub("link", text)
    text = _LIST_MARKER_RE.sub("", text)       # "- item" / "1. item" -> "item"
    text = re.sub(r"[*_`#>|{}\[\]]", "", text)
    text = text.replace("- ", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text
