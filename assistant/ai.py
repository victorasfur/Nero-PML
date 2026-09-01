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
import time
from typing import Dict, List, Optional

from config import settings
from .intents import AI_ALLOWED_INTENTS

_model = None
_init_failed = False


def _is_timeout(exc: Exception) -> bool:
    """True se a exceção da API for por estouro de tempo (timeout/deadline)."""
    name = type(exc).__name__.lower()
    return "timeout" in name or "deadline" in name


def _is_quota_error(exc: Exception) -> bool:
    """429 por cota/limite de requisições. Repetir NÃO ajuda — só gasta a cota
    mais rápido; então o retry ignora este caso de propósito."""
    name = type(exc).__name__.lower()
    if "resourceexhausted" in name or "toomanyrequests" in name:
        return True
    msg = str(exc).lower()
    return "429" in msg or "quota" in msg or "exceeded your current quota" in msg


def _is_transient(exc: Exception) -> bool:
    """Erros de servidor que costumam passar numa segunda tentativa
    (500/502/503/504, indisponibilidade momentânea). NÃO inclui 429: cota
    estourada não melhora com retry."""
    if _is_quota_error(exc):
        return False
    name = type(exc).__name__.lower()
    if any(k in name for k in ("unavailable", "internalserver", "servererror", "aborted")):
        return True
    msg = str(exc)
    return any(code in msg for code in ("500", "502", "503", "504"))


# Marcadores de que a pergunta pede uma EXPLICAÇÃO (mais tempo / mais tokens).
_COMPLEX_MARKERS = (
    "explique", "explica", "explicar", "por que", "porque",
    "como funciona", "como que", "detalhe", "detalha", "compare", "comparar",
    "diferenca", "diferencas", "resuma", "resumo", "passo a passo",
    "me conte", "conte sobre", "fale sobre", "o que e", "o que significa",
    "para que serve", "vantagens", "desvantagens", "pros e contras",
    "me ajuda a entender", "qual a relacao", "o que voce acha",
)


def _looks_complex(history: List[Dict[str, str]]) -> bool:
    """Heurística barata: última fala do usuário longa ou com marcador de
    explicação => trata como pergunta complexa."""
    last_user = ""
    for m in reversed(history):
        if m.get("role") == "user":
            last_user = (m.get("content") or "").lower()
            break
    if len(last_user) >= 120 or len(last_user.split()) >= 18:
        return True
    return any(mark in last_user for mark in _COMPLEX_MARKERS)

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

        # transport="rest": o transporte padrão (gRPC) faz a própria
        # verificação de TLS fora do módulo ssl do Python (nem o truststore
        # em main.py/app.py alcança) e exige negociação ALPN estrita, que
        # proxies corporativos de inspecao de TLS (Zscaler etc.) costumam
        # quebrar mesmo com o certificado do proxy instalado no sistema —
        # trava em "Handshake failed... CERTIFICATE_VERIFY_FAILED" ou,
        # depois de resolvido, em "missing selected ALPN property". REST usa
        # o mesmo caminho HTTPS comum (requests/ssl) que já funciona nessas
        # redes.
        genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")
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

    complex_q = _looks_complex(history)
    max_tokens = (
        settings.AI_MAX_OUTPUT_TOKENS_COMPLEX if complex_q else settings.AI_MAX_OUTPUT_TOKENS
    )
    timeout = (
        settings.GEMINI_CHAT_COMPLEX_TIMEOUT_SECONDS if complex_q
        else settings.GEMINI_CHAT_TIMEOUT_SECONDS
    )
    hard_cap = settings.GEMINI_CHAT_COMPLEX_TIMEOUT_SECONDS * 2
    attempts = 1 + max(0, settings.GEMINI_CHAT_RETRIES)
    if complex_q:
        print(f"[IA] pergunta complexa: timeout {timeout:.0f}s, até {attempts} tentativas.")

    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            response = model.generate_content(
                contents,
                generation_config={"temperature": 0.4, "max_output_tokens": max_tokens},
                request_options={"timeout": timeout},
            )
            text = (getattr(response, "text", "") or "").strip()
            if text:
                return text
            last_exc = None  # resposta vazia: tenta de novo se ainda houver tentativa
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if _is_quota_error(e):
                # Cota da API estourada: repetir só piora. Aborta já.
                print(f"[ERRO] Cota da API do Gemini esgotada: {e}")
                return (
                    "A cota diária da inteligência artificial foi atingida. "
                    "Tente de novo mais tarde ou troque o modelo no arquivo .env."
                )
            retriable = _is_timeout(e) or _is_transient(e)
            print(
                f"[IA] tentativa {attempt}/{attempts} falhou "
                f"({'timeout' if _is_timeout(e) else e})."
            )
            if attempt < attempts and retriable:
                timeout = min(timeout * 1.5, hard_cap)
                time.sleep(0.6 * attempt)
                continue
            break

    if last_exc is not None and _is_timeout(last_exc):
        return "Demorei demais para responder essa. Pode repetir a pergunta?"
    if last_exc is not None:
        print(f"[ERRO] Falha ao consultar a IA generativa: {last_exc}")
        return "Desculpe, não consegui obter uma resposta da inteligência artificial agora."
    return "Desculpe, não consegui pensar em uma resposta agora."


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
            generation_config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
                "max_output_tokens": 120,
            },
            request_options={"timeout": settings.GEMINI_CLASSIFY_TIMEOUT_SECONDS},
        )
        data = _extract_json(getattr(response, "text", "") or "")
    except Exception as e:  # noqa: BLE001
        if _is_timeout(e):
            print("[AVISO] Classificação por IA excedeu o tempo limite; seguindo para CHAT.")
        else:
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
