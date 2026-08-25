"""Command registry: Intent -> handler(params, normalized_text, raw_text).

Handlers não sabem NADA sobre como a intenção foi reconhecida (regex, fuzzy
match, o que for) — só recebem a intenção já decidida e os parâmetros já
extraídos. Isso é o que permite trocar o mecanismo de reconhecimento
(intent_router.py) sem tocar em nenhum handler.

dispatch() é o caminho normal (classifica + aplica a política de confiança).
execute() roda um Intent já determinado diretamente — usado tanto por
dispatch() quanto pelo loop principal quando o usuário confirma um "você
quis dizer X?" de confiança média.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import agenda, ai, calculator, datetime_utils, finance, screenshot, volume, weather, youtube
from .intent_router import CONFIDENCE_CONFIRM, CONFIDENCE_EXECUTE, INTENT_DESCRIPTIONS, IntentMatch, classify
from .intents import Intent
from .state_machine import AssistantState
from config import settings
from vision import face_recognition


@dataclass
class CommandResult:
    speak: Optional[str] = None
    speak_lines: Optional[List[str]] = None
    next_state: AssistantState = AssistantState.WAITING_WAKE_WORD
    # Preenchido só quando a confiança é média: o loop principal guarda isso
    # e, se o usuário confirmar, chama execute(pending_match.intent, ...).
    pending_match: Optional[IntentMatch] = None
    pending_raw_text: Optional[str] = None


# --- handlers -------------------------------------------------------------
# Assinatura única, independente do mecanismo de reconhecimento:
#   handler(params: dict, normalized_text: str, raw_text: str) -> CommandResult

def handle_get_date(params, normalized, raw) -> CommandResult:
    return CommandResult(speak=datetime_utils.get_date_response())


def handle_get_time(params, normalized, raw) -> CommandResult:
    return CommandResult(speak=datetime_utils.get_time_response())


def handle_add_agenda(params, normalized, raw) -> CommandResult:
    return CommandResult(
        speak="Ok, qual evento devo cadastrar?",
        next_state=AssistantState.WAITING_AGENDA_EVENT,
    )


def handle_read_agenda(params, normalized, raw) -> CommandResult:
    events = agenda.read_events()
    if not events:
        return CommandResult(speak="Sua agenda está vazia.")
    plural = "s" if len(events) != 1 else ""
    lines = [f"Você possui {len(events)} evento{plural} cadastrado{plural}."] + events
    return CommandResult(speak_lines=lines)


def handle_clear_agenda(params, normalized, raw) -> CommandResult:
    return CommandResult(
        speak="Tem certeza que deseja limpar sua agenda?",
        next_state=AssistantState.WAITING_CONFIRMATION_CLEAR_AGENDA,
    )


def handle_calculate(params, normalized, raw) -> CommandResult:
    expression = params.get("expression", normalized)
    value, error = calculator.calculate(expression)
    if error == "division_by_zero":
        speak = "Não é possível dividir por zero."
    elif error == "invalid_expression":
        speak = "Desculpe, não consegui entender essa conta. Tente algo como: quanto é dez mais vinte."
    else:
        speak = f"O resultado é {calculator.format_result(value)}."
    return CommandResult(speak=speak)


def handle_face_recognition(params, normalized, raw) -> CommandResult:
    return CommandResult(speak=face_recognition.recognize_face())


def handle_weather(params, normalized, raw) -> CommandResult:
    city = params.get("city") or settings.DEFAULT_CITY
    return CommandResult(speak=weather.get_weather_response(city))


def handle_dollar(params, normalized, raw) -> CommandResult:
    return CommandResult(speak=finance.get_dollar_response())


def handle_bitcoin(params, normalized, raw) -> CommandResult:
    return CommandResult(speak=finance.get_bitcoin_response())


def handle_youtube_search(params, normalized, raw) -> CommandResult:
    query = params.get("query", "").strip()
    try:
        youtube.search_youtube(query)
        speak = f"Pesquisando por {query} no YouTube."
    except Exception as e:
        print(f"[ERRO] Falha ao pesquisar no YouTube: {e}")
        speak = "Não consegui pesquisar no YouTube."
    return CommandResult(speak=speak)


def handle_open_youtube(params, normalized, raw) -> CommandResult:
    try:
        youtube.open_youtube()
        speak = "Abrindo o YouTube."
    except Exception as e:
        print(f"[ERRO] Falha ao abrir o YouTube: {e}")
        speak = "Não consegui abrir o YouTube."
    return CommandResult(speak=speak)


def handle_screenshot(params, normalized, raw) -> CommandResult:
    try:
        path = screenshot.take_screenshot()
        speak = f"Print da tela salvo como {path.name}."
    except Exception as e:
        print(f"[ERRO] Falha ao tirar screenshot: {e}")
        speak = "Não consegui tirar o print da tela."
    return CommandResult(speak=speak)


def handle_volume_up(params, normalized, raw) -> CommandResult:
    ok = volume.increase_volume()
    speak = "Volume aumentado." if ok else "Não consegui ajustar o volume neste computador."
    return CommandResult(speak=speak)


def handle_volume_down(params, normalized, raw) -> CommandResult:
    ok = volume.decrease_volume()
    speak = "Volume diminuído." if ok else "Não consegui ajustar o volume neste computador."
    return CommandResult(speak=speak)


def handle_ask_ai(params, normalized, raw) -> CommandResult:
    return CommandResult(speak=ai.ask_ai(raw))


# --- registro ---------------------------------------------------------

COMMAND_REGISTRY: Dict[Intent, Callable] = {
    Intent.GET_DATE: handle_get_date,
    Intent.GET_TIME: handle_get_time,
    Intent.ADD_AGENDA: handle_add_agenda,
    Intent.READ_AGENDA: handle_read_agenda,
    Intent.CLEAR_AGENDA: handle_clear_agenda,
    Intent.CALCULATE: handle_calculate,
    Intent.FACE_RECOGNITION: handle_face_recognition,
    Intent.WEATHER: handle_weather,
    Intent.DOLLAR: handle_dollar,
    Intent.BITCOIN: handle_bitcoin,
    Intent.YOUTUBE_SEARCH: handle_youtube_search,
    Intent.OPEN_YOUTUBE: handle_open_youtube,
    Intent.SCREENSHOT: handle_screenshot,
    Intent.VOLUME_UP: handle_volume_up,
    Intent.VOLUME_DOWN: handle_volume_down,
    Intent.ASK_AI: handle_ask_ai,
}


def execute(intent: Intent, params: dict, normalized_text: str, raw_text: str) -> CommandResult:
    handler = COMMAND_REGISTRY.get(intent, handle_ask_ai)
    try:
        return handler(params, normalized_text, raw_text)
    except Exception as e:
        print(f"[ERRO] Falha ao executar a intenção '{intent.name}': {e}")
        return CommandResult(speak="Desculpe, ocorreu um erro ao executar esse comando.")


def dispatch(normalized_text: str, raw_text: str) -> CommandResult:
    match = classify(normalized_text)

    if match.confidence >= CONFIDENCE_EXECUTE:
        return execute(match.intent, match.params, normalized_text, raw_text)

    if match.confidence >= CONFIDENCE_CONFIRM:
        description = INTENT_DESCRIPTIONS.get(match.intent, match.intent.name)
        return CommandResult(
            speak=f"Você quis dizer: {description}? Responda sim ou não.",
            next_state=AssistantState.WAITING_CONFIRM_INTENT,
            pending_match=match,
            pending_raw_text=raw_text,
        )

    return execute(Intent.ASK_AI, {}, normalized_text, raw_text)
