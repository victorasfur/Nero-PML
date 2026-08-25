import time
from enum import Enum, auto


class AssistantState(Enum):
    WAITING_WAKE_WORD = auto()
    WAITING_COMMAND = auto()
    WAITING_AGENDA_EVENT = auto()
    WAITING_CONFIRMATION_CLEAR_AGENDA = auto()


class StateMachine:
    """Controla o estado atual da assistente e há quanto tempo ele está ativo.

    Nenhum comando é executado fora de WAITING_COMMAND (ou do trecho de fala
    que já vem depois da wake word em WAITING_WAKE_WORD) — ver assistant.py.
    """

    def __init__(self):
        self.state = AssistantState.WAITING_WAKE_WORD
        self._entered_at = time.monotonic()

    def transition(self, new_state: AssistantState) -> None:
        self.state = new_state
        self._entered_at = time.monotonic()

    def seconds_in_state(self) -> float:
        return time.monotonic() - self._entered_at
