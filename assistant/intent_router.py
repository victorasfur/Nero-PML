"""Classificação de intenção: texto normalizado -> IntentMatch (intenção +
confiança + parâmetros), independente de como a intenção será executada
(isso fica em commands.py).

Estratégia HÍBRIDA, em ordem de prioridade:

1. Matchers ESTRUTURAIS (regex/parser dedicado, confiança alta): intenções
   com palavra-chave quase inequívoca e/ou que precisam de parâmetros
   (calculadora, música, busca no YouTube, abrir YouTube/navegador/Google/
   VS Code, clima, dólar, bitcoin, print, volume).

2. Guard de discurso: "fale sobre X" / "explique X" / "o que é X" é uma
   PERGUNTA, não um comando — vai para CHAT mesmo que X pareça uma intenção.

3. Fuzzy matching (rapidfuzz) contra frases de referência de
   data/intents.json — tolera reordenação e prefixos extras sem uma regra
   para cada variação.

4. Se o roteamento LOCAL ficou fraco (confiança < CONFIDENCE_CONFIRM) e a IA
   está disponível: `ai.classify_intent()` devolve {intent, confidence,
   parameters}, que é VALIDADO aqui contra o enum Intent + AI_ALLOWED_INTENTS
   + um schema de parâmetros. Ações vindas da IA nunca executam "no susto":
   no máximo entram na faixa de confirmação, salvo confiança bem alta.

5. Caso contrário: CHAT (conversa com a IA generativa).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from . import ai, calculator
from .intents import AI_ALLOWED_INTENTS, Intent
from .parameter_extractors import extract_music_query, extract_youtube_query
from .text_normalizer import normalize_text
from config import settings

# confidence >= EXECUTE: executa direto
# CONFIRM <= confidence < EXECUTE: pergunta "você quis dizer X?"
# confidence < CONFIRM: encaminha para a IA / CHAT
CONFIDENCE_EXECUTE = 0.80
CONFIDENCE_CONFIRM = 0.60

DISCOURSE_MARKERS = [
    "sobre", "explique", "explica", "explicar", "como funciona", "o que e",
    "o que significa", "conte uma historia", "me conte", "por que", "porque",
    "para que serve", "qual a diferenca", "qual e a diferenca",
]
# \b nas duas pontas: sem isso, "o que e" (sem acento = "o que é") também
# batia em qualquer "o que e<palavra>" — "o que EU tenho", "o que ESTA
# marcado", "o que ELE fez" — porque são só prefixos que começam com "e".
_DISCOURSE_RE = re.compile(r"\b(?:" + "|".join(re.escape(m) for m in DISCOURSE_MARKERS) + r")\b")

# Intenções resolvidas por fuzzy matching (as demais são só estruturais).
FUZZY_INTENTS = {
    Intent.GET_DATE, Intent.GET_TIME, Intent.ADD_AGENDA, Intent.READ_AGENDA,
    Intent.CLEAR_AGENDA, Intent.FACE_RECOGNITION, Intent.REGISTER_FACE, Intent.YOUTUBE_SEARCH,
    Intent.PLAY_MUSIC, Intent.OPEN_YOUTUBE, Intent.OPEN_BROWSER,
    Intent.OPEN_GOOGLE, Intent.OPEN_VSCODE, Intent.CHAT,
}


def _load_reference_phrases() -> Dict[Intent, List[str]]:
    phrases: Dict[Intent, List[str]] = {}
    try:
        data = json.loads(settings.INTENTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[AVISO] Não consegui ler {settings.INTENTS_FILE}: {e}")
        return phrases
    for name, payload in data.items():
        try:
            intent = Intent[name]
        except KeyError:
            continue
        if intent not in FUZZY_INTENTS:
            continue
        examples = [normalize_text(x) for x in payload.get("examples", []) if x.strip()]
        if examples:
            phrases[intent] = examples
    return phrases


REFERENCE_PHRASES: Dict[Intent, List[str]] = _load_reference_phrases()

INTENT_DESCRIPTIONS: Dict[Intent, str] = {
    Intent.GET_DATE: "saber a data de hoje",
    Intent.GET_TIME: "saber as horas",
    Intent.ADD_AGENDA: "cadastrar um evento na agenda",
    Intent.READ_AGENDA: "ler sua agenda",
    Intent.CLEAR_AGENDA: "limpar sua agenda",
    Intent.FACE_RECOGNITION: "fazer o reconhecimento facial",
    Intent.REGISTER_FACE: "cadastrar um novo rosto",
    Intent.YOUTUBE_SEARCH: "pesquisar vídeos no YouTube",
    Intent.PLAY_MUSIC: "tocar uma música no YouTube",
    Intent.OPEN_YOUTUBE: "abrir o YouTube",
    Intent.OPEN_BROWSER: "abrir o navegador",
    Intent.OPEN_GOOGLE: "abrir o Google",
    Intent.OPEN_VSCODE: "abrir o Visual Studio Code",
}


@dataclass
class IntentMatch:
    intent: Intent
    confidence: float
    params: dict = field(default_factory=dict)
    source: str = "local"  # local | discourse | fuzzy | ai | fallback (só p/ debug)


# --- matchers de música / YouTube / apps ---------------------------------

_MUSIC_VERBS_START = {
    "toque", "toca", "tocar", "poe", "poem", "bota", "botar", "coloca",
    "coloque", "colocar", "reproduz", "reproduza", "reproduzir", "canta", "cante",
}
_MUSIC_NOUNS = {"musica", "musicas", "cancao", "cancoes", "som", "playlist"}
_MUSIC_PHRASES = (
    "ouvir musica", "escutar musica", "ouvir uma musica", "escutar uma musica",
    "coloca uma musica", "poe uma musica", "quero ouvir", "quero escutar",
    "coloca pra tocar", "poe pra tocar",
)
_MUSIC_STOP_STARTS = {
    "no", "na", "nos", "nas", "sobre", "de", "do", "da", "que", "como", "o",
    "um", "uma", "pra", "para", "com", "isso", "sua", "seu",
}
_VAGUE_QUERIES = {"alguma coisa", "qualquer coisa", "coisa", "algo", "umas coisas"}

_YT_SEARCH_VERBS = ("pesquis", "procur", "busca", "busque", "acha", "ache", "encontr", "mostra", "mostre")
_OPEN_VERB = r"(abr[ae]|abrir|inicia|iniciar|executa|executar|entr[ae]|entrar|acess[ae]|acessar|vai|va)"

_OPEN_YT_RE = re.compile(rf"\b{_OPEN_VERB}\b.*\byoutube\b")
_APP_PATTERNS: List[Tuple[Intent, "re.Pattern"]] = [
    (Intent.OPEN_VSCODE, re.compile(rf"\b{_OPEN_VERB}\b.*\b(vs ?code|visual studio code|editor de codigo)\b")),
    (Intent.OPEN_BROWSER, re.compile(rf"\b{_OPEN_VERB}\b.*\b(navegador|chrome|firefox|edge|browser)\b")),
    (Intent.OPEN_GOOGLE, re.compile(rf"\b{_OPEN_VERB}\b.*\bgoogle\b")),
]


def _match_play_music(text: str) -> Optional[IntentMatch]:
    tokens = text.split()
    has_noun = bool(_MUSIC_NOUNS & set(tokens))
    starts_verb = bool(tokens) and tokens[0] in _MUSIC_VERBS_START
    phrase_hit = any(p in text for p in _MUSIC_PHRASES)
    if not (has_noun or starts_verb or phrase_hit):
        return None

    query = extract_music_query(text)
    if query in _VAGUE_QUERIES:
        query = ""
    if query and not has_noun:
        q0 = query.split()[0]
        if q0 in _MUSIC_STOP_STARTS:
            return None
    return IntentMatch(Intent.PLAY_MUSIC, 0.92, {"query": query})


def _match_youtube_search(text: str) -> Optional[IntentMatch]:
    has_yt = "youtube" in text
    has_video = "video" in text or "videos" in text
    has_verb = (
        any(v in text for v in _YT_SEARCH_VERBS)
        or "quero ver" in text
        or "quero assistir" in text
        or "quero video" in text
    )
    if has_yt and not has_video and not has_verb:
        return None  # provavelmente OPEN_YOUTUBE
    if not (has_yt or (has_video and has_verb)):
        return None

    query = extract_youtube_query(text)
    if not query or query in _VAGUE_QUERIES:
        return None
    return IntentMatch(Intent.YOUTUBE_SEARCH, 0.9, {"query": query})


def _match_open_youtube(text: str) -> Optional[IntentMatch]:
    if "youtube" not in text:
        return None
    if _OPEN_YT_RE.search(text) or "assistir" in text or "ver alguma coisa" in text or text.strip() == "youtube":
        return IntentMatch(Intent.OPEN_YOUTUBE, 1.0, {})
    return None


def _match_open_app(text: str) -> Optional[IntentMatch]:
    for intent, pattern in _APP_PATTERNS:
        if pattern.search(text):
            return IntentMatch(intent, 1.0, {})
    return None


def _structural_match(text: str) -> Optional[IntentMatch]:
    _, error = calculator.calculate(text)
    if error is None:
        return IntentMatch(Intent.CALCULATE, 1.0, {"expression": text})

    # Regexes de alta precisão ANTES das heurísticas soltas de música/YouTube
    # (ex.: "aumenta o som" é volume, não pedido de música).
    patterns: List[Tuple[Intent, "re.Pattern", callable]] = [
        (Intent.WEATHER,
         re.compile(r"(previsao do tempo|como esta o tempo|como esta o clima|vai chover)( para| em)? ?(?P<city>.+)?"),
         lambda m: {"city": (m.group("city") or "").strip() or None}),
        (Intent.DOLLAR, re.compile(r"(valor do dolar|quanto esta o dolar|cotacao do dolar)"), lambda m: {}),
        (Intent.BITCOIN, re.compile(r"(vale.*bitcoin|bitcoin.*vale|valor.*bitcoin|quanto esta o bitcoin|preco do bitcoin)"),
         lambda m: {}),
        (Intent.SCREENSHOT, re.compile(r"(tirar|tira|fazer|faca|faz) (uma |um )?(print|captura|screenshot|foto da tela)"),
         lambda m: {}),
        (Intent.VOLUME_UP, re.compile(r"(aumentar|aumenta|sobe|subir)( o)? (volume|som)"), lambda m: {}),
        (Intent.VOLUME_DOWN, re.compile(r"(diminuir|diminui|abaixa|abaixar|baixa)( o)? (volume|som)"), lambda m: {}),
        (Intent.EASTER_EGG_CORINTHIANS, re.compile(r"\b(vai|vamos)\s+corinthians\b"), lambda m: {}),
        # .{0,15} entre o verbo e "piada(s)": cobre "conte uma piada", "me
        # conta uma piada", "sabe alguma piada" sem virar um "contém a
        # palavra piada em algum lugar da frase" solto demais.
        (Intent.EASTER_EGG_JOKE, re.compile(r"\b(conte|conta|fala|fale|sabe)\b.{0,15}\bpiadas?\b"), lambda m: {}),
        # (?!\s+tarde): "ate mais" sozinho é despedida, mas "ate mais TARDE"
        # é só uma referência de tempo ("eu volto ate mais tarde") — não deve
        # encerrar a assistente.
        (Intent.SHUTDOWN, re.compile(r"\bate mais\b(?!\s+tarde)|\bate logo\b|\btchau\b"), lambda m: {}),
    ]
    for intent, pattern, extract_params in patterns:
        m = pattern.search(text)
        if m:
            return IntentMatch(intent, 1.0, extract_params(m))

    for matcher in (_match_play_music, _match_youtube_search, _match_open_youtube, _match_open_app):
        result = matcher(text)
        if result is not None:
            return result
    return None


def _best_fuzzy_match(text: str) -> Tuple[Optional[Intent], float]:
    best_intent = None
    best_score = 0.0
    for intent, phrases in REFERENCE_PHRASES.items():
        result = process.extractOne(text, phrases, scorer=fuzz.token_sort_ratio)
        if result is None:
            continue
        _, score, _ = result
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent, best_score


def _fill_params(match: IntentMatch, normalized_text: str) -> None:
    if match.intent == Intent.YOUTUBE_SEARCH and not match.params.get("query"):
        match.params["query"] = extract_youtube_query(normalized_text)
    elif match.intent == Intent.PLAY_MUSIC and not match.params.get("query"):
        match.params["query"] = extract_music_query(normalized_text)


# --- validação da classificação por IA ---------------------------------

def _sanitize_ai_params(intent: Intent, params) -> dict:
    """Só copiamos chaves CONHECIDAS por intent — nunca um dict arbitrário
    vindo da IA (blindagem contra parâmetros injetados)."""
    if not isinstance(params, dict):
        return {}
    out: dict = {}
    if intent in (Intent.YOUTUBE_SEARCH, Intent.PLAY_MUSIC):
        q = str(params.get("query", "")).strip()
        if q:
            out["query"] = q
    elif intent == Intent.WEATHER:
        city = str(params.get("city", "")).strip()
        if city:
            out["city"] = city
    elif intent == Intent.CALCULATE:
        expr = str(params.get("expression", "")).strip()
        if expr:
            out["expression"] = expr
    return out


def _ai_match(text: str, history) -> Optional[IntentMatch]:
    if not settings.AI_INTENT_CLASSIFICATION_ENABLED or not ai.is_available():
        return None
    data = ai.classify_intent(text, history)
    if not data:
        return None
    try:
        intent = Intent[str(data.get("intent", "")).strip().upper()]
    except KeyError:
        return None
    if intent not in AI_ALLOWED_INTENTS:
        return None

    if intent == Intent.CHAT:
        return IntentMatch(Intent.CHAT, 1.0, {}, source="ai")

    conf = float(data.get("confidence", 0.0) or 0.0)
    params = _sanitize_ai_params(intent, data.get("parameters", {}))
    if intent in (Intent.YOUTUBE_SEARCH, Intent.PLAY_MUSIC) and not params.get("query"):
        params["query"] = extract_youtube_query(text) if intent == Intent.YOUTUBE_SEARCH else extract_music_query(text)

    if conf >= 0.85:
        conf = 0.85            # executa
    elif conf >= 0.5:
        conf = CONFIDENCE_CONFIRM  # pede "você quis dizer X?"
    else:
        return IntentMatch(Intent.CHAT, 1.0, {}, source="ai")
    return IntentMatch(intent, conf, params, source="ai")


# --- API pública -------------------------------------------------------

def classify(normalized_text: str, raw_text: Optional[str] = None, history=None,
             allow_ai: bool = True) -> IntentMatch:
    """normalized_text já sem a wake word e já passado por normalize_text().
    raw_text (opcional) é a fala original, usada só pela classificação por IA.
    allow_ai=False força roteamento 100% local e determinístico (testes)."""
    if not normalized_text:
        return IntentMatch(Intent.CHAT, 1.0, {}, source="fallback")

    structural = _structural_match(normalized_text)
    if structural:
        _fill_params(structural, normalized_text)
        return structural

    if _DISCOURSE_RE.search(normalized_text):
        return IntentMatch(Intent.CHAT, 1.0, {}, source="discourse")

    best_intent, best_score = _best_fuzzy_match(normalized_text)
    local_conf = (best_score / 100.0) if best_intent is not None else 0.0
    if best_intent is not None and local_conf >= CONFIDENCE_CONFIRM:
        match = IntentMatch(best_intent, local_conf, {}, source="fuzzy")
        _fill_params(match, normalized_text)
        return match

    ai_match = _ai_match(raw_text or normalized_text, history) if allow_ai else None
    if ai_match is not None:
        return ai_match

    return IntentMatch(Intent.CHAT, 1.0, {}, source="fallback")


def detect_intent(text: str) -> Intent:
    """Conveniência para testes: roteamento LOCAL apenas (sem IA), já
    aplicando o limiar de execução — abaixo dele o resultado visível é CHAT."""
    match = classify(normalize_text(text), raw_text=text, allow_ai=False)
    if match.confidence < CONFIDENCE_EXECUTE:
        return Intent.CHAT
    return match.intent
