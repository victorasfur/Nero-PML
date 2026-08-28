import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
AGENDA_FILE = DATA_DIR / "agenda.txt"
INTENTS_FILE = DATA_DIR / "intents.json"
DATASET_DIR = BASE_DIR / "vision" / "dataset"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# Palavra de ativação: variantes toleradas e limiar de similaridade (difflib.SequenceMatcher).
# Só a palavra inicial da frase é comparada, para evitar falsos positivos no meio da fala.
WAKE_WORD_VARIANTS = ["nero", "niro", "neru"]
WAKE_WORD_SIMILARITY_THRESHOLD = 0.75

# Reconhecimento de voz (SpeechRecognition + Google Web Speech API).
LISTEN_TIMEOUT_SECONDS = 5
LISTEN_PHRASE_TIME_LIMIT = 8

# adjust_for_ambient_noise() às vezes calibra um limiar de energia absurdamente
# alto em microfones USB baratos/com ruído de driver, o que faz o reconhecedor
# nunca detectar fala nenhuma. Se isso acontecer, caímos para um valor mais
# sensível conhecido por funcionar bem na maioria dos microfones.
MIC_ENERGY_THRESHOLD_CEILING = 4000
MIC_ENERGY_THRESHOLD_FALLBACK = 300

# Segundos sem fala válida em um estado de espera (comando/agenda/confirmação)
# até reverter automaticamente para WAITING_WAKE_WORD.
COMMAND_TIMEOUT_SECONDS = 12

DEFAULT_CITY = "São Paulo"

# --- IA generativa (Google Gemini) --------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
# O nome do modelo do Gemini muda com o tempo (a Google aposenta versões
# antigas); se a API começar a responder "model ... is no longer available",
# atualize o valor padrão abaixo ou defina GEMINI_MODEL no .env.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

# Se False, a assistente funciona 100% offline para os comandos locais e
# responde educadamente que a conversa por IA não está disponível.
GEMINI_ENABLED = bool(GEMINI_API_KEY)

# Também usar a IA para CLASSIFICAR pedidos que o roteamento local não
# resolveu com confiança. Só tem efeito se GEMINI_ENABLED. Desligue para um
# comportamento totalmente determinístico.
AI_INTENT_CLASSIFICATION_ENABLED = True

# Instrução de sistema da conversa (a resposta será FALADA em voz alta).
AI_SYSTEM_PROMPT = (
    "Você é uma assistente virtual chamada Nero. "
    "Responda sempre em português do Brasil. "
    "Seja natural, clara e objetiva. "
    "Suas respostas serão faladas em voz alta, então evite respostas longas "
    "(no máximo 3 ou 4 frases) e não use formatação como markdown, asteriscos, "
    "listas numeradas longas ou blocos de código. "
    "Quando precisar enumerar, use no máximo 3 itens curtos. "
    "Não invente informações; se não souber, diga que não sabe."
)

# Janela de contexto da conversa: quantas mensagens (user + assistant) manter.
CONVERSATION_MAX_MESSAGES = 20

# --- Ações de sistema: allowlist de alvos --------------------------------------
# A IA NUNCA fornece um caminho/URL/comando: ela só devolve uma INTENÇÃO
# (ex.: OPEN_VSCODE) e o código local resolve o alvo por esta tabela fixa.
WEB_TARGETS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "navegador": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
}

# Candidatos de instalação do VS Code no Windows (resolvidos em ordem).
VSCODE_CANDIDATES = [
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe"),
]

# LBPH: quanto MENOR a confiança, melhor o match. Acima do limiar = "Desconhecido".
LBPH_CONFIDENCE_THRESHOLD = 80
FACE_CAPTURE_COUNT = 20
