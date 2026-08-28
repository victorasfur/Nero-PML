"""Extração de parâmetros a partir do texto JÁ NORMALIZADO (minúsculas, sem
acento/pontuação).

Só heurística leve de recorte de prefixo/sufixo — nada de NLP pesado. Quando
o texto é vago demais ("aquela musica que fala eu sei que vou te amar"), o
que sobra ainda é uma query utilizável, e a classificação por IA
(ai.classify_intent) pode devolver uma query melhor.
"""

import re

# Verbos/expressoes que costumam iniciar um pedido de tocar musica.
_MUSIC_LEAD = [
    "toca pra tocar", "coloca pra tocar", "poe pra tocar", "bota pra tocar",
    "quero ouvir", "quero escutar", "quero que voce toque", "manda tocar",
    "toque", "toca", "tocar", "coloque", "coloca", "colocar",
    "poe", "poem", "bota", "botar", "reproduza", "reproduz", "reproduzir",
    "manda", "quero", "canta", "cante",
]

# Ruído comum ao redor do nome da música.
_MUSIC_FILLER = [
    "aquela musica que fala", "aquela cancao que fala", "a musica que fala",
    "aquela musica", "aquela cancao", "uma musica", "a musica", "musica",
    "cancao", "uma cancao", "um som", "som", "para mim", "pra mim", "ai",
]

_MUSIC_TRAIL = [
    "no youtube", "pelo youtube", "no spotify", "pra tocar", "para tocar",
    "por favor", "agora", "ai",
]

_YT_LEAD = [
    "pesquise", "pesquisa", "pesquisar", "procure", "procura", "procurar",
    "busque", "busca", "buscar", "acha", "ache", "achar", "encontre",
    "me mostra", "me mostre", "mostra", "mostre", "quero ver", "quero assistir",
    "quero", "quero um video", "quero videos", "quero um video de",
]

_YT_FILLER = [
    "videos sobre", "video sobre", "videos de", "video de", "um video sobre",
    "um video de", "um video ensinando", "video ensinando", "videos", "video",
    "sobre", "de",
]

_YT_TRAIL = ["no youtube", "pelo youtube", "por favor", "agora"]


def _strip_prefixes(text: str, prefixes) -> str:
    changed = True
    while changed:
        changed = False
        for p in sorted(prefixes, key=len, reverse=True):
            if text == p:
                return ""
            if text.startswith(p + " "):
                text = text[len(p) + 1:].strip()
                changed = True
                break
    return text


def _strip_suffixes(text: str, suffixes) -> str:
    changed = True
    while changed:
        changed = False
        for s in sorted(suffixes, key=len, reverse=True):
            if text == s:
                return ""
            if text.endswith(" " + s):
                text = text[: -(len(s) + 1)].strip()
                changed = True
                break
    return text


def _drop_youtube_tokens(text: str) -> str:
    """Remove "youtube" e conectores ("no youtube", "pelo youtube") em
    qualquer posição — o roteador já decidiu que é YouTube, a palavra em si
    não faz parte da query."""
    text = re.sub(r"\b(no|na|nos|nas|pelo|pela|do|da|pra|para|para o|em)\s+youtube\b", " ", text)
    text = re.sub(r"\byoutube\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_music_query(normalized_text: str) -> str:
    text = re.sub(r"\s+", " ", (normalized_text or "").strip())
    text = _drop_youtube_tokens(text)
    text = _strip_prefixes(text, _MUSIC_LEAD)
    text = _strip_prefixes(text, _MUSIC_FILLER)
    text = _strip_suffixes(text, _MUSIC_TRAIL)
    text = _strip_prefixes(text, _MUSIC_LEAD)
    text = _strip_prefixes(text, _MUSIC_FILLER)
    return text.strip()


def extract_youtube_query(normalized_text: str) -> str:
    text = re.sub(r"\s+", " ", (normalized_text or "").strip())
    text = _drop_youtube_tokens(text)
    text = _strip_suffixes(text, _YT_TRAIL)
    text = _strip_prefixes(text, _YT_LEAD)
    text = _strip_prefixes(text, _YT_FILLER)
    text = _strip_prefixes(text, _YT_LEAD)
    text = _strip_suffixes(text, _YT_TRAIL)
    return text.strip()
