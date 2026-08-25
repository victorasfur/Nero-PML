import difflib
import re
import unicodedata
from typing import Tuple

from config import settings


def normalize_text(text: str) -> str:
    """minusculas, sem acento, sem pontuação, espaços colapsados."""
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_wake_word(normalized_text: str) -> Tuple[bool, int]:
    """Verifica se a PRIMEIRA palavra da fala é a wake word (com tolerância a
    variações de transcrição). Checar só a primeira palavra evita falsos
    positivos (ex.: "fui na loja da alexa" não deve ativar a assistente).

    Retorna (encontrou, quantidade_de_palavras_consumidas).
    """
    if not normalized_text:
        return False, 0
    first_word = normalized_text.split()[0]
    for variant in settings.WAKE_WORD_VARIANTS:
        ratio = difflib.SequenceMatcher(None, first_word, variant).ratio()
        if ratio >= settings.WAKE_WORD_SIMILARITY_THRESHOLD:
            return True, 1
    return False, 0
