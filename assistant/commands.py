"""Registro declarativo de comandos + roteador.

Cada comando é um par (regex, handler). O primeiro que der match no texto
normalizado é executado. Se nenhum der match, a fala é encaminhada para a IA
generativa (assistant.ai.ask_ai). Adicionar um comando novo = adicionar uma
entrada em COMMANDS, sem tocar no loop principal da assistente.
"""

import re
from dataclasses import dataclass
from typing import Callable, List, Optional

from . import agenda, ai, calculator, datetime_utils, finance, screenshot, volume, weather, youtube
from .state_machine import AssistantState
from config import settings
from vision import face_recognition


@dataclass
class CommandResult:
    speak: Optional[str] = None
    speak_lines: Optional[List[str]] = None
    next_state: AssistantState = AssistantState.WAITING_WAKE_WORD


@dataclass
class Command:
    name: str
    pattern: "re.Pattern"
    handler: Callable[["re.Match", str, str], CommandResult]


# --- handlers ---------------------------------------------------------

def handle_cadastrar_evento(match, normalized, raw) -> CommandResult:
    return CommandResult(
        speak="Ok, qual evento devo cadastrar?",
        next_state=AssistantState.WAITING_AGENDA_EVENT,
    )


def handle_limpar_agenda(match, normalized, raw) -> CommandResult:
    return CommandResult(
        speak="Tem certeza que deseja limpar sua agenda?",
        next_state=AssistantState.WAITING_CONFIRMATION_CLEAR_AGENDA,
    )


def handle_ler_agenda(match, normalized, raw) -> CommandResult:
    events = agenda.read_events()
    if not events:
        return CommandResult(speak="Sua agenda está vazia.")
    plural = "s" if len(events) != 1 else ""
    lines = [f"Você possui {len(events)} evento{plural} cadastrado{plural}."] + events
    return CommandResult(speak_lines=lines)


def handle_horas(match, normalized, raw) -> CommandResult:
    return CommandResult(speak=datetime_utils.get_time_response())


def handle_dia(match, normalized, raw) -> CommandResult:
    return CommandResult(speak=datetime_utils.get_date_response())


def handle_calcular(match, normalized, raw) -> CommandResult:
    expr = match.group(1)
    value, error = calculator.calculate(expr)
    if error == "division_by_zero":
        speak = "Não é possível dividir por zero."
    elif error == "invalid_expression":
        speak = "Desculpe, não consegui entender essa conta. Tente algo como: calcular dez mais vinte."
    else:
        speak = f"O resultado é {calculator.format_result(value)}."
    return CommandResult(speak=speak)


def handle_reconhecer_face(match, normalized, raw) -> CommandResult:
    return CommandResult(speak=face_recognition.recognize_face())


def handle_clima(match, normalized, raw) -> CommandResult:
    city = match.group("city") or settings.DEFAULT_CITY
    return CommandResult(speak=weather.get_weather_response(city))


def handle_dolar(match, normalized, raw) -> CommandResult:
    return CommandResult(speak=finance.get_dollar_response())


def handle_bitcoin(match, normalized, raw) -> CommandResult:
    return CommandResult(speak=finance.get_bitcoin_response())


def handle_pesquisar_youtube(match, normalized, raw) -> CommandResult:
    query = match.group(1).strip()
    try:
        youtube.search_youtube(query)
        speak = f"Pesquisando por {query} no YouTube."
    except Exception as e:
        print(f"[ERRO] Falha ao pesquisar no YouTube: {e}")
        speak = "Não consegui pesquisar no YouTube."
    return CommandResult(speak=speak)


def handle_abrir_youtube(match, normalized, raw) -> CommandResult:
    try:
        youtube.open_youtube()
        speak = "Abrindo o YouTube."
    except Exception as e:
        print(f"[ERRO] Falha ao abrir o YouTube: {e}")
        speak = "Não consegui abrir o YouTube."
    return CommandResult(speak=speak)


def handle_screenshot(match, normalized, raw) -> CommandResult:
    try:
        path = screenshot.take_screenshot()
        speak = f"Print da tela salvo como {path.name}."
    except Exception as e:
        print(f"[ERRO] Falha ao tirar screenshot: {e}")
        speak = "Não consegui tirar o print da tela."
    return CommandResult(speak=speak)


def handle_aumentar_volume(match, normalized, raw) -> CommandResult:
    ok = volume.increase_volume()
    speak = "Volume aumentado." if ok else "Não consegui ajustar o volume neste computador."
    return CommandResult(speak=speak)


def handle_diminuir_volume(match, normalized, raw) -> CommandResult:
    ok = volume.decrease_volume()
    speak = "Volume diminuído." if ok else "Não consegui ajustar o volume neste computador."
    return CommandResult(speak=speak)


# --- registro -----------------------------------------------------------
# Ordem importa apenas onde padrões poderiam colidir (ex.: "youtube"); comandos
# de agenda usam verbos distintos (cadastrar/limpar/ler) então não colidem entre si.

COMMANDS: List[Command] = [
    Command("cadastrar_evento", re.compile(r"cadastrar.*evento"), handle_cadastrar_evento),
    Command("limpar_agenda", re.compile(r"limpar.*agenda"), handle_limpar_agenda),
    Command("ler_agenda", re.compile(r"ler.*agenda"), handle_ler_agenda),
    Command("horas", re.compile(r"que horas"), handle_horas),
    Command("dia", re.compile(r"que dia"), handle_dia),
    Command("calcular", re.compile(r"calcular (.+)"), handle_calcular),
    Command("reconhecer_face", re.compile(r"(reconhecer face|quem sou eu)"), handle_reconhecer_face),
    Command("clima", re.compile(r"previsao do tempo( para (?P<city>.+))?"), handle_clima),
    Command("dolar", re.compile(r"valor do dolar"), handle_dolar),
    Command("bitcoin", re.compile(r"(vale.*bitcoin|bitcoin.*vale|valor.*bitcoin)"), handle_bitcoin),
    Command("pesquisar_youtube", re.compile(r"pesquisar no youtube (.+)"), handle_pesquisar_youtube),
    Command("abrir_youtube", re.compile(r"abrir( o)? youtube"), handle_abrir_youtube),
    Command("screenshot", re.compile(r"(tirar|fazer) (um )?print"), handle_screenshot),
    Command("aumentar_volume", re.compile(r"aumentar( o)? volume"), handle_aumentar_volume),
    Command("diminuir_volume", re.compile(r"diminuir( o)? volume"), handle_diminuir_volume),
]


def dispatch(normalized_text: str, raw_text: str) -> CommandResult:
    for command in COMMANDS:
        m = command.pattern.search(normalized_text)
        if m:
            try:
                return command.handler(m, normalized_text, raw_text)
            except Exception as e:
                print(f"[ERRO] Falha ao executar o comando '{command.name}': {e}")
                return CommandResult(speak="Desculpe, ocorreu um erro ao executar esse comando.")

    return CommandResult(speak=ai.ask_ai(raw_text))
