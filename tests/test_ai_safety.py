"""Garante que uma resposta da IA NÃO consegue fazer a aplicação executar
algo perigoso: a IA só devolve uma intenção estruturada; quem decide (e o
que é permitido) é o código local."""

import re
from pathlib import Path

import pytest

from assistant import intent_router
from assistant.intent_router import CONFIDENCE_EXECUTE, _ai_match, _sanitize_ai_params
from assistant.intents import AI_ALLOWED_INTENTS, Intent

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def force_ai(monkeypatch):
    """Finge que a IA está disponível e devolve `payload`."""
    def _install(payload):
        monkeypatch.setattr(intent_router.ai, "is_available", lambda: True)
        monkeypatch.setattr(intent_router.ai, "classify_intent", lambda text, history=None: payload)
        monkeypatch.setattr(intent_router.settings, "AI_INTENT_CLASSIFICATION_ENABLED", True)
    return _install


def test_ai_cannot_invent_a_shell_intent(force_ai):
    force_ai({"intent": "subprocess", "confidence": 0.99, "parameters": {"cmd": "rm -rf /"}})
    assert _ai_match("apague tudo", None) is None


def test_ai_cannot_pick_an_intent_outside_the_allowlist(force_ai):
    # CLEAR_AGENDA existe no enum, mas NÃO está em AI_ALLOWED_INTENTS.
    force_ai({"intent": "CLEAR_AGENDA", "confidence": 0.99, "parameters": {}})
    assert _ai_match("limpa a agenda", None) is None


def test_destructive_intents_are_not_ai_classifiable():
    for name in ("CLEAR_AGENDA", "ADD_AGENDA", "READ_AGENDA", "FACE_RECOGNITION"):
        assert Intent[name] not in AI_ALLOWED_INTENTS


def test_ai_action_never_executes_without_confirmation_unless_very_confident(force_ai):
    force_ai({"intent": "PLAY_MUSIC", "confidence": 0.7, "parameters": {"query": "evidencias"}})
    match = _ai_match("bota aquela musica", None)
    assert match.intent == Intent.PLAY_MUSIC
    assert match.confidence < CONFIDENCE_EXECUTE  # cai na faixa de confirmação

    force_ai({"intent": "PLAY_MUSIC", "confidence": 0.97, "parameters": {"query": "evidencias"}})
    match = _ai_match("bota aquela musica", None)
    assert match.confidence >= CONFIDENCE_EXECUTE


def test_sanitize_ai_params_drops_unknown_keys():
    params = _sanitize_ai_params(
        Intent.PLAY_MUSIC,
        {"query": "evidencias", "command": "powershell", "__import__": "os"},
    )
    assert params == {"query": "evidencias"}


def test_sanitize_ai_params_ignores_non_dict():
    assert _sanitize_ai_params(Intent.CHAT, "os.system('x')") == {}


def test_no_shell_execution_primitives_in_source():
    # Uso REAL (chamada/import), não menções em docstring/comentário.
    forbidden = re.compile(r"(^|\s)(import subprocess|subprocess\.\w+\(|os\.system\(|os\.popen\(|eval\(|exec\()")
    offenders = []
    for folder in ("assistant", "config", "vision"):
        for path in (ROOT / folder).rglob("*.py"):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith(("#", "-", '"""', '"')) or '"""' in line:
                    continue
                if forbidden.search(line):
                    offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, "primitivas de shell encontradas:\n" + "\n".join(offenders)
