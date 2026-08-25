"""Integração com IA generativa (Google Gemini). Chave lida do .env, nunca do código.

ask_ai() é usado como fallback: quando a fala do usuário não bate com nenhum
comando local conhecido, a pergunta é encaminhada para a IA.
"""

import google.generativeai as genai

from config import settings

_configured = False


def _ensure_configured() -> bool:
    global _configured
    if _configured:
        return True
    if not settings.GEMINI_API_KEY:
        return False
    genai.configure(api_key=settings.GEMINI_API_KEY)
    _configured = True
    return True


def ask_ai(question: str) -> str:
    if not question or not question.strip():
        return "Desculpe, não entendi sua pergunta."

    if not _ensure_configured():
        print("[AVISO] GEMINI_API_KEY não configurada no .env. Defina a chave para habilitar respostas de IA.")
        return "Desculpe, ainda não consigo responder isso. A integração com inteligência artificial não está configurada."

    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        prompt = (
            "Responda em português do Brasil, de forma direta e breve (no máximo 3 frases), "
            "pois a resposta será falada em voz alta por uma assistente virtual.\n\n"
            f"Pergunta: {question}"
        )
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return text if text else "Desculpe, não consegui pensar em uma resposta agora."
    except Exception as e:
        print(f"[ERRO] Falha ao consultar a IA generativa: {e}")
        return "Desculpe, não consegui obter uma resposta da inteligência artificial agora."
