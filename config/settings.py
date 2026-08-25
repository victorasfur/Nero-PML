import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
AGENDA_FILE = DATA_DIR / "agenda.txt"
DATASET_DIR = BASE_DIR / "vision" / "dataset"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# Palavra de ativação: variantes toleradas e limiar de similaridade (difflib.SequenceMatcher).
# Only a palavra inicial da frase é comparada, para evitar falsos positivos no meio da fala.
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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# O nome do modelo do Gemini muda com o tempo (a Google aposenta versões
# antigas); se a API começar a responder "model ... is no longer available",
# atualize o valor padrão abaixo ou defina GEMINI_MODEL no .env.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# LBPH: quanto MENOR a confiança, melhor o match. Acima do limiar = "Desconhecido".
LBPH_CONFIDENCE_THRESHOLD = 80
FACE_CAPTURE_COUNT = 20
