"""Persistência da agenda em texto puro (agenda.txt), sem banco de dados.

Todas as funções aceitam um `path` opcional (default: config.settings.AGENDA_FILE)
para permitir testes isolados sem tocar no arquivo real do usuário.
"""

from pathlib import Path
from typing import List, Optional

from config import settings


def ensure_agenda_file(path: Optional[Path] = None) -> None:
    path = path or settings.AGENDA_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


def add_event(text: str, path: Optional[Path] = None) -> None:
    path = path or settings.AGENDA_FILE
    ensure_agenda_file(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text.strip() + "\n")


def read_events(path: Optional[Path] = None) -> List[str]:
    path = path or settings.AGENDA_FILE
    ensure_agenda_file(path)
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def clear_agenda(path: Optional[Path] = None) -> None:
    """Esvazia o arquivo SEM excluí-lo — ele deve continuar existindo."""
    path = path or settings.AGENDA_FILE
    ensure_agenda_file(path)
    with open(path, "w", encoding="utf-8"):
        pass
