"""Loop principal: máquina de estados que garante que NENHUM comando é
executado antes da palavra de ativação "Alexa".

    WAITING_WAKE_WORD --"alexa"--> WAITING_COMMAND --comando--> WAITING_WAKE_WORD
                                        |
                                        +--> WAITING_AGENDA_EVENT --evento--> WAITING_WAKE_WORD
                                        +--> WAITING_CONFIRMATION_CLEAR_AGENDA --sim/não--> WAITING_WAKE_WORD
                                        +--> WAITING_CONFIRM_INTENT --sim/não--> WAITING_WAKE_WORD

Se "Alexa" e o comando vierem na mesma fala ("Alexa, que horas são?"), o
restante da frase é executado imediatamente após a wake word ser detectada.

WAITING_CONFIRM_INTENT existe porque intent_router.classify() pode ter
confiança média num palpite (fuzzy matching) — nesse caso o comando NÃO é
executado direto; a assistente pergunta "você quis dizer X?" e só executa
depois de uma confirmação explícita (ver commands.dispatch / CONFIDENCE_*).
"""

from colorama import Fore, Style
from colorama import init as colorama_init

from . import agenda, commands
from .intents import Intent
from .speech import InputClosed, SpeechEngine
from .state_machine import AssistantState, StateMachine
from .text_normalizer import detect_wake_word, normalize_text
from config import settings

colorama_init()


def print_banner() -> None:
    print("=" * 48)
    print("        ALEXA - ASSISTENTE VIRTUAL")
    print("=" * 48)
    print()


def print_status(msg: str) -> None:
    print(f"{Fore.YELLOW}Status: {msg}{Style.RESET_ALL}")


def print_user(msg: str) -> None:
    print(f"{Fore.CYAN}Você: {msg}{Style.RESET_ALL}")


class Assistant:
    def __init__(self, text_mode: bool = False, mic_index: int = None):
        agenda.ensure_agenda_file()
        self.speech = SpeechEngine(text_mode=text_mode, mic_index=mic_index)
        self.sm = StateMachine()
        self._pending_match = None
        self._pending_raw_text = None

    def run(self) -> None:
        print_banner()
        print_status("aguardando palavra de ativação...")
        while True:
            try:
                self._tick()
            except KeyboardInterrupt:
                print()
                print_status("encerrando assistente. Até logo!")
                break
            except InputClosed as e:
                print_status(f"encerrando assistente ({e}). Até logo!")
                break

    # -- ciclo principal ---------------------------------------------------

    def _tick(self) -> None:
        state = self.sm.state

        if state != AssistantState.WAITING_WAKE_WORD and self.sm.seconds_in_state() > settings.COMMAND_TIMEOUT_SECONDS:
            self.sm.transition(AssistantState.WAITING_WAKE_WORD)
            print_status("tempo esgotado, aguardando palavra de ativação...")
            return

        raw_text = self.speech.listen()
        if raw_text is None:
            return

        normalized = normalize_text(raw_text)

        if state == AssistantState.WAITING_WAKE_WORD:
            self._handle_waiting_wake_word(raw_text, normalized)
        elif state == AssistantState.WAITING_COMMAND:
            self._handle_waiting_command(raw_text, normalized)
        elif state == AssistantState.WAITING_AGENDA_EVENT:
            self._handle_agenda_event(raw_text, normalized)
        elif state == AssistantState.WAITING_CONFIRMATION_CLEAR_AGENDA:
            self._handle_clear_agenda_confirmation(raw_text, normalized)
        elif state == AssistantState.WAITING_CONFIRM_INTENT:
            self._handle_confirm_intent(raw_text, normalized)

    # -- estados -------------------------------------------------------

    def _handle_waiting_wake_word(self, raw_text: str, normalized: str) -> None:
        if not normalized:
            return
        print_user(raw_text)

        found, consumed = detect_wake_word(normalized)
        if not found:
            print_status("comando ignorado. Assistente não ativada.")
            return

        print_status("assistente ativada.")
        raw_remainder = " ".join(raw_text.split()[consumed:]).strip()
        norm_remainder = " ".join(normalized.split()[consumed:]).strip()

        if not norm_remainder:
            self.sm.transition(AssistantState.WAITING_COMMAND)
            self.speech.speak("Pode falar.")
            return

        self._execute_command(norm_remainder, raw_remainder)

    def _handle_waiting_command(self, raw_text: str, normalized: str) -> None:
        print_user(raw_text)
        if not normalized:
            self.speech.speak("Desculpe, não consegui entender.")
            return
        if normalized == "cancelar":
            self._cancel("Operação cancelada.")
            return
        self._execute_command(normalized, raw_text)

    def _handle_agenda_event(self, raw_text: str, normalized: str) -> None:
        print_user(raw_text)
        if normalized == "cancelar":
            self._cancel("Operação cancelada.")
            return
        if not raw_text.strip():
            self.speech.speak("Desculpe, não consegui entender. Qual evento devo cadastrar?")
            return
        agenda.add_event(raw_text.strip())
        self.speech.speak("Evento cadastrado com sucesso.")
        self.sm.transition(AssistantState.WAITING_WAKE_WORD)
        print_status("aguardando palavra de ativação...")

    def _handle_clear_agenda_confirmation(self, raw_text: str, normalized: str) -> None:
        print_user(raw_text)
        tokens = set(normalized.split())
        yes_words = {"sim", "confirmo", "certo", "isso"}
        no_words = {"nao", "negativo"}

        if tokens & yes_words:
            agenda.clear_agenda()
            self.speech.speak("Agenda limpa com sucesso.")
            self.sm.transition(AssistantState.WAITING_WAKE_WORD)
            print_status("aguardando palavra de ativação...")
        elif tokens & no_words:
            self.speech.speak("Ok, não vou apagar nada.")
            self.sm.transition(AssistantState.WAITING_WAKE_WORD)
            print_status("aguardando palavra de ativação...")
        else:
            self.speech.speak("Não entendi, pode responder sim ou não?")

    def _handle_confirm_intent(self, raw_text: str, normalized: str) -> None:
        print_user(raw_text)

        if normalized in ("cancelar", "cancela"):
            self._pending_match = None
            self._pending_raw_text = None
            self._cancel("Tudo bem, operação cancelada.")
            return

        tokens = set(normalized.split())
        yes_words = {"sim", "confirmo", "certo", "isso"}
        no_words = {"nao", "negativo"}

        if tokens & yes_words:
            match = self._pending_match
            self._pending_match = None
            self._pending_raw_text = None
            result = commands.execute(match.intent, match.params, normalized, raw_text)
            self._apply_result(result)
        elif tokens & no_words:
            pending_raw = self._pending_raw_text
            self._pending_match = None
            self._pending_raw_text = None
            result = commands.execute(Intent.ASK_AI, {}, normalized, pending_raw)
            self._apply_result(result)
        else:
            self.speech.speak("Não entendi, pode responder sim ou não?")

    # -- utilidades ---------------------------------------------------

    def _execute_command(self, normalized: str, raw_text: str) -> None:
        result = commands.dispatch(normalized, raw_text)
        self._apply_result(result)

    def _apply_result(self, result) -> None:
        if result.speak:
            self.speech.speak(result.speak)
        if result.speak_lines:
            for line in result.speak_lines:
                self.speech.speak(line)

        self._pending_match = result.pending_match
        self._pending_raw_text = result.pending_raw_text
        self.sm.transition(result.next_state)

        status_by_state = {
            AssistantState.WAITING_WAKE_WORD: "aguardando palavra de ativação...",
            AssistantState.WAITING_AGENDA_EVENT: "aguardando descrição do evento...",
            AssistantState.WAITING_CONFIRMATION_CLEAR_AGENDA: "aguardando confirmação (sim/não)...",
            AssistantState.WAITING_CONFIRM_INTENT: "aguardando confirmação da intenção (sim/não)...",
        }
        print_status(status_by_state[result.next_state])

    def _cancel(self, message: str) -> None:
        self.sm.transition(AssistantState.WAITING_WAKE_WORD)
        self.speech.speak(message)
        print_status("aguardando palavra de ativação...")
