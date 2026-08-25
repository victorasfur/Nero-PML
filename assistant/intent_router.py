"""Classificação de intenção: transforma texto normalizado em um IntentMatch
(intenção + confiança + parâmetros), independente de como a intenção acabará
sendo executada (isso fica em command_registry, dentro de commands.py).

Estratégia híbrida, em ordem de prioridade:

1. Matchers ESTRUTURAIS (regex/parser dedicado, confiança sempre 1.0): usados
   para intenções com uma palavra-chave praticamente inequívoca e que
   costumam precisar de parâmetros (calculadora, clima, dólar, bitcoin,
   YouTube, print, volume). Regex generaliza mal para "várias formas de
   dizer a mesma coisa" mas é exatamente certo aqui, e barato.

2. Guard de discurso: frases como "fale sobre X" / "explique X" / "o que é
   X" indicam uma PERGUNTA sobre o assunto, não um comando — mesmo que X
   seja lexicalmente parecido com uma intenção (ex.: "fale sobre
   reconhecimento facial" não deve abrir a câmera). Isso força ASK_AI antes
   mesmo de tentar o fuzzy matching.

3. Fuzzy matching (rapidfuzz): para intenções com MUITAS formas naturais de
   serem ditas (data, hora, agenda, reconhecimento facial), comparamos o
   texto contra uma lista curada de frases de referência usando WRatio —
   combina razão de caracteres com sobreposição de palavras (token/partial
   ratio), o que lida bem tanto com reordenação ("hoje é que dia" vs. "que
   dia é hoje") quanto com prefixos extras ("você pode me dizer que dia é
   hoje"), sem precisar de uma regra para cada variação possível.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from . import calculator
from .intents import Intent
from .text_normalizer import normalize_text

# confidence >= EXECUTE: executa direto
# CONFIRM <= confidence < EXECUTE: pergunta "você quis dizer X?"
# confidence < CONFIRM: encaminha para a IA
CONFIDENCE_EXECUTE = 0.80
CONFIDENCE_CONFIRM = 0.60

DISCOURSE_MARKERS = [
    "sobre", "explique", "explica", "como funciona", "o que e", "conte uma historia", "me conte",
]

REFERENCE_PHRASES: Dict[Intent, List[str]] = {
    Intent.GET_DATE: [
        "que dia e hoje",
        "qual o dia de hoje",
        "qual a data de hoje",
        "voce sabe que dia e hoje",
        "voce pode me dizer que dia e hoje",
        "voce sabe me dizer qual e a data de hoje",
        "voce pode me dizer a data de hoje",
        "me fala que dia e hoje",
        "me fala a data",
        "me diga a data de hoje",
        "poderia me informar a data de hoje",
        "hoje e que dia",
        "que dia estamos hoje",
        "em que dia estamos",
        "pode falar a data de hoje",
        "me informe o dia de hoje",
        "qual a data",
    ],
    Intent.GET_TIME: [
        "que horas sao",
        "qual e a hora",
        "voce sabe que horas sao",
        "voce pode me dizer a hora",
        "voce pode me dizer que horas sao",
        "me fala as horas",
        "me fala a hora",
        "pode me dizer a hora",
        "que horas temos agora",
        "me informe o horario",
        "qual o horario atual",
        "sabe me dizer a hora atual",
        "poderia informar o horario",
        "qual a hora",
    ],
    Intent.ADD_AGENDA: [
        "cadastrar evento na agenda",
        "adicione um evento na minha agenda",
        "quero cadastrar um evento",
        "quero adicionar um compromisso",
        "quero colocar um compromisso na minha agenda",
        "quero colocar um evento na agenda",
        "coloque um evento na agenda",
        "adiciona isso na minha agenda",
        "marque um compromisso",
        "quero marcar um evento",
        "pode adicionar um evento",
        "preciso cadastrar um compromisso",
    ],
    Intent.READ_AGENDA: [
        "ler agenda",
        "leia minha agenda",
        "quais sao meus eventos",
        "quais compromissos eu tenho",
        "o que tenho na agenda",
        "me mostra minha agenda",
        "me fale meus compromissos",
        "quais eventos estao cadastrados",
        "quero consultar minha agenda",
        "pode consultar minha agenda",
        "o que esta marcado para mim",
    ],
    Intent.CLEAR_AGENDA: [
        "limpar agenda",
        "apague minha agenda",
        "quero limpar minha agenda",
        "pode apagar os eventos",
        "remova todos os eventos",
        "exclua os eventos da agenda",
        "quero apagar minha agenda",
        "delete os compromissos",
        "remova tudo da agenda",
    ],
    Intent.FACE_RECOGNITION: [
        "reconhecer face",
        "reconheca meu rosto",
        "quem sou eu",
        "voce sabe quem eu sou",
        "me reconheca",
        "pode reconhecer meu rosto",
        "abra a camera e me reconheca",
        "identificar pessoa",
        "identifique quem esta na frente",
    ],
}

INTENT_DESCRIPTIONS: Dict[Intent, str] = {
    Intent.GET_DATE: "saber a data de hoje",
    Intent.GET_TIME: "saber as horas",
    Intent.ADD_AGENDA: "cadastrar um evento na agenda",
    Intent.READ_AGENDA: "ler sua agenda",
    Intent.CLEAR_AGENDA: "limpar sua agenda",
    Intent.FACE_RECOGNITION: "fazer o reconhecimento facial",
}


@dataclass
class IntentMatch:
    intent: Intent
    confidence: float
    params: dict = field(default_factory=dict)


def _structural_match(text: str) -> Optional[IntentMatch]:
    value, error = calculator.calculate(text)
    if error is None:
        return IntentMatch(Intent.CALCULATE, 1.0, {"expression": text})

    patterns: List[Tuple[Intent, "re.Pattern", callable]] = [
        (Intent.YOUTUBE_SEARCH, re.compile(r"pesquisar no youtube (.+)"),
         lambda m: {"query": m.group(1).strip()}),
        (Intent.OPEN_YOUTUBE, re.compile(r"abrir( o)? youtube"), lambda m: {}),
        (Intent.WEATHER,
         re.compile(r"(previsao do tempo|como esta o tempo|como esta o clima|vai chover)( para| em)? ?(?P<city>.+)?"),
         lambda m: {"city": (m.group("city") or "").strip() or None}),
        (Intent.DOLLAR, re.compile(r"(valor do dolar|quanto esta o dolar|cotacao do dolar)"), lambda m: {}),
        (Intent.BITCOIN, re.compile(r"(vale.*bitcoin|bitcoin.*vale|valor.*bitcoin|quanto esta o bitcoin)"),
         lambda m: {}),
        (Intent.SCREENSHOT, re.compile(r"(tirar|fazer) (um )?print"), lambda m: {}),
        (Intent.VOLUME_UP, re.compile(r"aumentar( o)? volume"), lambda m: {}),
        (Intent.VOLUME_DOWN, re.compile(r"diminuir( o)? volume"), lambda m: {}),
    ]
    for intent, pattern, extract_params in patterns:
        m = pattern.search(text)
        if m:
            return IntentMatch(intent, 1.0, extract_params(m))
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


def classify(normalized_text: str) -> IntentMatch:
    """normalized_text já deve ter passado por normalize_text() (e sem a
    wake word, que é removida antes disso no loop principal)."""
    if not normalized_text:
        return IntentMatch(Intent.ASK_AI, 1.0, {})

    structural = _structural_match(normalized_text)
    if structural:
        return structural

    if any(marker in normalized_text for marker in DISCOURSE_MARKERS):
        return IntentMatch(Intent.ASK_AI, 1.0, {})

    best_intent, best_score = _best_fuzzy_match(normalized_text)
    if best_intent is None:
        return IntentMatch(Intent.ASK_AI, 1.0, {})
    return IntentMatch(best_intent, best_score / 100, {})


def detect_intent(text: str) -> Intent:
    """Conveniência para testes: normaliza, classifica e já aplica o limiar
    de execução — abaixo dele, o resultado "visível" é sempre ASK_AI (é o
    que a política real do assistente faria com esse nível de confiança)."""
    match = classify(normalize_text(text))
    if match.confidence < CONFIDENCE_EXECUTE:
        return Intent.ASK_AI
    return match.intent
