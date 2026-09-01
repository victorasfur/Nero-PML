"""Command registry: Intent -> handler(params, normalized_text, raw_text, memory).

Handlers não sabem NADA sobre COMO a intenção foi reconhecida (regex, fuzzy,
IA) — só recebem a intenção já decidida, os parâmetros já extraídos e (só o
handler de conversa usa) a memória da conversa. Isso permite trocar o
mecanismo de reconhecimento (intent_router.py) sem tocar em nenhum handler.

SEGURANÇA: nenhum handler executa comando de shell/SO com string vinda de
fora. Abrir apps/sites passa por assistant/system_actions.py, que só aceita
CHAVES de um allowlist fixo — a IA nunca fornece caminho/URL/comando.

dispatch() é o caminho normal (classifica + aplica a política de confiança).
execute() roda um Intent já determinado — usado por dispatch() e pelo loop
principal quando o usuário confirma um "você quis dizer X?".
"""

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from . import (
    agenda, ai, calculator, datetime_utils, finance, screenshot, system_actions,
    volume, weather, youtube,
)
from .intent_router import (
    CONFIDENCE_CONFIRM, CONFIDENCE_EXECUTE, INTENT_DESCRIPTIONS, IntentMatch, classify,
)
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
    # True só para o comando de encerrar: fala a despedida normalmente e o
    # loop principal (assistant.py) sai depois de falar, sem precisar de
    # exceção nem estado novo na máquina de estados.
    shutdown: bool = False


# --- handlers -----------------------------------------------------------
# Assinatura única: handler(params, normalized_text, raw_text, memory) -> CommandResult
# (memory é um ConversationMemory ou None; só o handler de conversa o usa.)

def handle_get_date(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak=datetime_utils.get_date_response())


def handle_get_time(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak=datetime_utils.get_time_response())


def handle_add_agenda(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(
        speak="Ok, qual evento devo cadastrar?",
        next_state=AssistantState.WAITING_AGENDA_EVENT,
    )


def handle_read_agenda(params, normalized, raw, memory) -> CommandResult:
    events = agenda.read_events()
    if not events:
        return CommandResult(speak="Sua agenda está vazia.")
    plural = "s" if len(events) != 1 else ""
    lines = [f"Você possui {len(events)} evento{plural} cadastrado{plural}."] + events
    return CommandResult(speak_lines=lines)


def handle_clear_agenda(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(
        speak="Tem certeza que deseja limpar sua agenda?",
        next_state=AssistantState.WAITING_CONFIRMATION_CLEAR_AGENDA,
    )


def handle_calculate(params, normalized, raw, memory) -> CommandResult:
    expression = params.get("expression", normalized)
    value, error = calculator.calculate(expression)
    if error == "division_by_zero":
        speak = "Não é possível dividir por zero."
    elif error == "invalid_expression":
        speak = "Desculpe, não consegui entender essa conta. Tente algo como: quanto é dez mais vinte."
    else:
        speak = f"O resultado é {calculator.format_result(value)}."
    return CommandResult(speak=speak)


def handle_face_recognition(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak=face_recognition.recognize_face())


def handle_register_face(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(
        speak="Qual o nome da pessoa que eu devo cadastrar?",
        next_state=AssistantState.WAITING_FACE_NAME,
    )


def handle_weather(params, normalized, raw, memory) -> CommandResult:
    city = params.get("city") or settings.DEFAULT_CITY
    return CommandResult(speak=weather.get_weather_response(city))


def handle_dollar(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak=finance.get_dollar_response())


def handle_bitcoin(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak=finance.get_bitcoin_response())


def handle_open_youtube(params, normalized, raw, memory) -> CommandResult:
    try:
        youtube.open_youtube()
        speak = "Abrindo o YouTube."
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao abrir o YouTube: {e}")
        speak = "Não consegui abrir o YouTube."
    return CommandResult(speak=speak)


def handle_youtube_search(params, normalized, raw, memory) -> CommandResult:
    query = (params.get("query") or "").strip()
    if not query:
        return CommandResult(speak="O que você quer pesquisar no YouTube?")
    try:
        youtube.search_youtube(query)
        speak = f"Vou procurar {query} no YouTube."
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao pesquisar no YouTube: {e}")
        speak = "Não consegui pesquisar no YouTube."
    return CommandResult(speak=speak)


def handle_play_music(params, normalized, raw, memory) -> CommandResult:
    query = (params.get("query") or "").strip()
    if not query:
        return CommandResult(
            speak="Não entendi o nome da música. Tente dizer, por exemplo: toque Evidências."
        )
    try:
        youtube.search_youtube(query)
        # Não afirmamos que "começou a tocar": o navegador não garante autoplay.
        speak = f"Encontrei {query}. Abrindo no YouTube."
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao abrir o YouTube: {e}")
        speak = "Não consegui abrir o YouTube agora."
    return CommandResult(speak=speak)


def handle_open_browser(params, normalized, raw, memory) -> CommandResult:
    ok = system_actions.open_browser()
    return CommandResult(speak="Abrindo o navegador." if ok else "Não consegui abrir o navegador.")


def handle_open_google(params, normalized, raw, memory) -> CommandResult:
    ok = system_actions.open_google()
    return CommandResult(speak="Abrindo o Google." if ok else "Não consegui abrir o Google.")


def handle_open_vscode(params, normalized, raw, memory) -> CommandResult:
    ok = system_actions.open_vscode()
    return CommandResult(
        speak="Abrindo o Visual Studio Code." if ok
        else "Não encontrei o Visual Studio Code instalado neste computador."
    )


def handle_screenshot(params, normalized, raw, memory) -> CommandResult:
    try:
        path = screenshot.take_screenshot()
        speak = f"Print da tela salvo como {path.name}."
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao tirar screenshot: {e}")
        speak = "Não consegui tirar o print da tela."
    return CommandResult(speak=speak)


def handle_volume_up(params, normalized, raw, memory) -> CommandResult:
    ok = volume.increase_volume()
    speak = "Volume aumentado." if ok else "Não consegui ajustar o volume neste computador."
    return CommandResult(speak=speak)


def handle_volume_down(params, normalized, raw, memory) -> CommandResult:
    ok = volume.decrease_volume()
    speak = "Volume diminuído." if ok else "Não consegui ajustar o volume neste computador."
    return CommandResult(speak=speak)


def handle_easter_egg_corinthians(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak="Vai Corinthians!!!")


_JOKES = [
    "Por que a aranha é o animal mais carente do mundo? Porque ela é um arac need you.",
    "Por que o pinheiro não se perde na floresta? Porque ele tem uma pinha.",
    "O que o cavalo foi fazer no orelhão? Passar um trote!",
]


def handle_easter_egg_joke(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak=random.choice(_JOKES))


def handle_shutdown(params, normalized, raw, memory) -> CommandResult:
    return CommandResult(speak="Até mais!", shutdown=True)


def handle_chat(params, normalized, raw, memory) -> CommandResult:
    if memory is not None and len(memory) > 0:
        history = memory.history()
    else:
        history = [{"role": "user", "content": raw or normalized}]
    print("[IA] Enviando pergunta para o Gemini...")
    return CommandResult(speak=ai.ask_chat(history))


# --- registro ---------------------------------------------------------

COMMAND_REGISTRY: Dict[Intent, Callable] = {
    Intent.GET_DATE: handle_get_date,
    Intent.GET_TIME: handle_get_time,
    Intent.ADD_AGENDA: handle_add_agenda,
    Intent.READ_AGENDA: handle_read_agenda,
    Intent.CLEAR_AGENDA: handle_clear_agenda,
    Intent.CALCULATE: handle_calculate,
    Intent.FACE_RECOGNITION: handle_face_recognition,
    Intent.REGISTER_FACE: handle_register_face,
    Intent.WEATHER: handle_weather,
    Intent.DOLLAR: handle_dollar,
    Intent.BITCOIN: handle_bitcoin,
    Intent.OPEN_YOUTUBE: handle_open_youtube,
    Intent.YOUTUBE_SEARCH: handle_youtube_search,
    Intent.PLAY_MUSIC: handle_play_music,
    Intent.OPEN_BROWSER: handle_open_browser,
    Intent.OPEN_GOOGLE: handle_open_google,
    Intent.OPEN_VSCODE: handle_open_vscode,
    Intent.SCREENSHOT: handle_screenshot,
    Intent.VOLUME_UP: handle_volume_up,
    Intent.VOLUME_DOWN: handle_volume_down,
    Intent.EASTER_EGG_CORINTHIANS: handle_easter_egg_corinthians,
    Intent.EASTER_EGG_JOKE: handle_easter_egg_joke,
    Intent.SHUTDOWN: handle_shutdown,
    Intent.CHAT: handle_chat,
}


def execute(intent: Intent, params: dict, normalized_text: str, raw_text: str, memory=None) -> CommandResult:
    handler = COMMAND_REGISTRY.get(intent, handle_chat)
    print(f"[AÇÃO] {intent.name}")
    if params:
        for key, value in params.items():
            print(f"[PARÂMETRO] {key} = {value}")
    try:
        return handler(params, normalized_text, raw_text, memory)
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao executar a intenção '{intent.name}': {e}")
        return CommandResult(speak="Desculpe, ocorreu um erro ao executar esse comando.")


def dispatch(normalized_text: str, raw_text: str, memory=None) -> CommandResult:
    history = memory.history() if memory is not None else None
    match = classify(normalized_text, raw_text=raw_text, history=history)

    print(f"[INTENÇÃO] {match.intent.name}  [CONFIANÇA] {match.confidence:.2f}  [ORIGEM] {match.source}")

    if match.confidence >= CONFIDENCE_EXECUTE:
        return execute(match.intent, match.params, normalized_text, raw_text, memory)

    if match.confidence >= CONFIDENCE_CONFIRM and match.intent != Intent.CHAT:
        description = INTENT_DESCRIPTIONS.get(match.intent, match.intent.name)
        return CommandResult(
            speak=f"Você quis dizer: {description}? Responda sim ou não.",
            next_state=AssistantState.WAITING_CONFIRM_INTENT,
            pending_match=match,
            pending_raw_text=raw_text,
        )

    return execute(Intent.CHAT, {}, normalized_text, raw_text, memory)
