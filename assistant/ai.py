"""Integração com IA generativa (Google Gemini).

Dois papéis SEPARADOS, de propósito:

- `ask_chat(history)`  -> PROSA. É o "cérebro conversacional". A resposta é
  falada em voz alta. Nunca recebe pedido de "execute X".

- `classify_intent(text, history)` -> JSON {intent, confidence, parameters}.
  Usado só quando o roteamento LOCAL não resolveu com confiança. O resultado
  é VALIDADO em intent_router contra o enum Intent + um schema de parâmetros
  antes de qualquer execução. Este JSON JAMAIS é falado.

A chave vem do .env (config.settings), nunca do código. Sem chave / sem
internet, `is_available()` é False e a assistente continua funcionando para
todos os comandos locais.
"""

import json
import re
from typing import Dict, List, Optional

from config import settings
from .intents import AI_ALLOWED_INTENTS

_model = None
_init_failed = False

_INTENT_MENU = """\
GET_DATE: usuário quer saber a data de hoje
GET_TIME: usuário quer saber as horas
CALCULATE: conta de matemática simples (+, -, x, ÷). parameters.expression = expressão em texto
WEATHER: previsão do tempo. parameters.city = cidade (opcional)
DOLLAR: cotação do dólar
BITCOIN: cotação do bitcoin
OPEN_YOUTUBE: abrir o YouTube (sem busca)
YOUTUBE_SEARCH: pesquisar VÍDEOS no YouTube. parameters.query = o que buscar
PLAY_MUSIC: tocar uma MÚSICA/artista/gênero. parameters.query = música ou artista
OPEN_BROWSER: abrir o navegador
OPEN_GOOGLE: abrir o Google
OPEN_VSCODE: abrir o VS Code / editor de código
SCREENSHOT: tirar um print da tela
VOLUME_UP: aumentar o volume
VOLUME_DOWN: diminuir o volume
CHAT: qualquer outra coisa (pergunta geral, conversa, curiosidade, piada)"""


def _ensure_model():
    global _model, _init_failed
    if _model is not None:
        return _model
    if _init_failed or not settings.GEMINI_ENABLED:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=settings.AI_SYSTEM_PROMPT,
        )
        return _model
    except Exception as e:  # noqa: BLE001
        print(f"[AVISO] Não foi possível iniciar a IA generativa: {e}")
        _init_failed = True
        return None


def is_available() -> bool:
    return _ensure_model() is not None


# --- conversa ---------------------------------------------------------------

def ask_chat(history: List[Dict[str, str]]) -> str:
    """history: lista [{'role': 'user'|'assistant', 'content': str}] já
    terminando na última fala do usuário."""
    model = _ensure_model()
    if model is None:
        return (
            "A conversa por inteligência artificial não está configurada agora, "
            "mas posso te ajudar com os comandos locais."
        )
    if not history:
        return "Desculpe, não entendi sua pergunta."

    contents = [
        {"role": ("model" if m["role"] == "assistant" else "user"), "parts": [m["content"]]}
        for m in history
    ]
    try:
        response = model.generate_content(contents)
        text = (getattr(response, "text", "") or "").strip()
        return text or "Desculpe, não consegui pensar em uma resposta agora."
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha ao consultar a IA generativa: {e}")
        return "Desculpe, não consegui obter uma resposta da inteligência artificial agora."


def ask_ai(question: str) -> str:
    """Compatibilidade com a versão anterior (uma pergunta avulsa, sem histórico)."""
    return ask_chat([{"role": "user", "content": question or ""}])


# --- classificação -------------------------------------------------------

def _extract_json(raw: str) -> Optional[dict]:
    raw = (raw or "").strip()
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def classify_intent(text: str, history: Optional[List[Dict[str, str]]] = None) -> Optional[dict]:
    """Devolve {'intent': str, 'confidence': float, 'parameters': dict} ou None.

    NÃO valida contra o enum aqui — isso é responsabilidade de intent_router
    (_ai_match). Aqui só garantimos o formato mínimo.
    """
    model = _ensure_model()
    if model is None or not (text or "").strip():
        return None

    allowed = ", ".join(sorted(i.name for i in AI_ALLOWED_INTENTS))
    context = ""
    if history:
        recent = history[-6:]
        lines = [f"{m['role']}: {m['content']}" for m in recent]
        context = "Contexto recente da conversa (para resolver 'ele', 'isso', 'aquela'):\n" + "\n".join(lines) + "\n\n"

    prompt = (
        "Você é um classificador de intenção de uma assistente de voz. "
        "Leia o pedido do usuário e responda APENAS com um JSON, sem texto fora dele, "
        'no formato: {"intent": "NOME", "confidence": 0.0-1.0, "parameters": {}}.\n\n'
        f"Intenções válidas (use exatamente um destes nomes): {allowed}\n\n"
        f"{_INTENT_MENU}\n\n"
        "Regras: se for uma pergunta geral ou conversa, use CHAT com parameters vazio. "
        "Para YOUTUBE_SEARCH e PLAY_MUSIC preencha parameters.query com o termo limpo "
        "(sem 'toca', 'procure', 'no youtube'). "
        "confidence alta (>=0.85) só quando tiver certeza.\n\n"
        f"{context}"
        f'Pedido do usuário: "{text.strip()}"'
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.0, "response_mime_type": "application/json"},
        )
        data = _extract_json(getattr(response, "text", "") or "")
    except Exception as e:  # noqa: BLE001
        print(f"[ERRO] Falha na classificação por IA: {e}")
        return None

    if not isinstance(data, dict) or "intent" not in data:
        return None
    intent_name = str(data.get("intent", "")).strip().upper()
    if not intent_name:
        return None
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    parameters = data.get("parameters") or {}
    if not isinstance(parameters, dict):
        parameters = {}
    return {
        "intent": intent_name,
        "confidence": max(0.0, min(1.0, confidence)),
        "parameters": parameters,
    }
