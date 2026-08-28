"""Contexto de conversa: uma janela deslizante das últimas N mensagens.

Guarda pares (usuário / assistente) para que a IA generativa consiga
resolver referências como "e onde ELE nasceu?" ou "e Java?" logo depois de
uma pergunta sobre Einstein ou Python.

Não cresce infinitamente: sempre que passa de `max_messages`, as mensagens
mais antigas são descartadas (ver `_trim`).
"""

from dataclasses import dataclass, field
from typing import Dict, List

from config import settings

USER = "user"
ASSISTANT = "assistant"


@dataclass
class ConversationMemory:
    max_messages: int = settings.CONVERSATION_MAX_MESSAGES
    _messages: List[Dict[str, str]] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self._add(USER, content)

    def add_assistant(self, content: str) -> None:
        self._add(ASSISTANT, content)

    def _add(self, role: str, content: str) -> None:
        content = (content or "").strip()
        if not content:
            return
        self._messages.append({"role": role, "content": content})
        self._trim()

    def _trim(self) -> None:
        if self.max_messages > 0 and len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def history(self) -> List[Dict[str, str]]:
        """Cópia da janela atual, no formato [{'role': ..., 'content': ...}]."""
        return [dict(m) for m in self._messages]

    def as_gemini_contents(self) -> List[Dict[str, object]]:
        """Mesma janela no formato que o SDK do Gemini espera
        ('assistant' -> 'model', texto dentro de 'parts')."""
        contents = []
        for m in self._messages:
            role = "model" if m["role"] == ASSISTANT else "user"
            contents.append({"role": role, "parts": [m["content"]]})
        return contents

    def last_user_message(self) -> str:
        for m in reversed(self._messages):
            if m["role"] == USER:
                return m["content"]
        return ""

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
