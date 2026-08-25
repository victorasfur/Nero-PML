import pytest

from assistant.intent_router import CONFIDENCE_EXECUTE, classify, detect_intent
from assistant.intents import Intent
from assistant.text_normalizer import detect_wake_word, normalize_text


def _route(text):
    """Simula o pipeline real: normaliza e remove a wake word antes de classificar."""
    normalized = normalize_text(text)
    found, consumed = detect_wake_word(normalized)
    remainder = " ".join(normalized.split()[consumed:]) if found else normalized
    return classify(remainder)


@pytest.mark.parametrize("text", [
    "que dia e hoje",
    "qual a data de hoje",
    "me fala a data de hoje",
    "voce sabe que dia e hoje",
    "hoje e que dia",
    "que dia estamos hoje",
    "em que dia estamos",
    "qual o dia de hoje",
    "poderia me informar a data de hoje",
    "me informe o dia de hoje",
])
def test_get_date(text):
    assert detect_intent(text) == Intent.GET_DATE


@pytest.mark.parametrize("text", [
    "que horas sao",
    "qual e a hora",
    "voce sabe que horas sao",
    "me fala as horas",
    "pode me dizer a hora",
    "que horas temos agora",
    "qual o horario atual",
    "sabe me dizer a hora atual",
    "poderia informar o horario",
])
def test_get_time(text):
    assert detect_intent(text) == Intent.GET_TIME


@pytest.mark.parametrize("text", [
    "cadastrar evento na agenda",
    "adicione um evento na minha agenda",
    "quero cadastrar um evento",
    "quero adicionar um compromisso",
    "coloque um evento na agenda",
    "adiciona isso na minha agenda",
    "marque um compromisso",
    "quero marcar um evento",
    "pode adicionar um evento",
    "preciso cadastrar um compromisso",
])
def test_add_agenda(text):
    assert detect_intent(text) == Intent.ADD_AGENDA


@pytest.mark.parametrize("text", [
    "ler agenda",
    "leia minha agenda",
    "quais sao meus eventos",
    "quais compromissos eu tenho",
    "o que tenho na agenda",
    "me mostra minha agenda",
    "me fale meus compromissos",
    "quais eventos estao cadastrados",
    "quero consultar minha agenda",
    "pode consultar minha agenda",
])
def test_read_agenda(text):
    assert detect_intent(text) == Intent.READ_AGENDA


@pytest.mark.parametrize("text", [
    "limpar agenda",
    "apague minha agenda",
    "quero limpar minha agenda",
    "pode apagar os eventos",
    "remova todos os eventos",
    "exclua os eventos da agenda",
    "quero apagar minha agenda",
    "delete os compromissos",
    "remova tudo da agenda",
])
def test_clear_agenda(text):
    assert detect_intent(text) == Intent.CLEAR_AGENDA


@pytest.mark.parametrize("text", [
    "calcular 10 mais 20",
    "quanto e 10 mais 20",
    "quanto da 10 + 20",
    "calcule 10 somado com 20",
    "faca uma conta 10 mais 20",
    "quanto e 50 menos 20",
    "calcule 8 vezes 7",
    "quanto e 100 dividido por 4",
    "faca 20 multiplicado por 5",
    "100 dividido por 5",
])
def test_calculate(text):
    assert detect_intent(text) == Intent.CALCULATE


@pytest.mark.parametrize("text", [
    "reconhecer face",
    "reconheca meu rosto",
    "quem sou eu",
    "voce sabe quem eu sou",
    "me reconheca",
    "pode reconhecer meu rosto",
    "identificar pessoa",
    "identifique quem esta na frente",
])
def test_face_recognition(text):
    assert detect_intent(text) == Intent.FACE_RECOGNITION


@pytest.mark.parametrize("text", [
    "qual a previsao do tempo para sao paulo",
    "previsao do tempo",
    "como esta o tempo",
])
def test_weather(text):
    assert detect_intent(text) == Intent.WEATHER


@pytest.mark.parametrize("text", ["qual o valor do dolar hoje", "quanto esta o dolar"])
def test_dollar(text):
    assert detect_intent(text) == Intent.DOLLAR


@pytest.mark.parametrize("text", ["quanto vale um bitcoin hoje", "quanto esta o bitcoin"])
def test_bitcoin(text):
    assert detect_intent(text) == Intent.BITCOIN


def test_open_youtube():
    assert detect_intent("abrir youtube") == Intent.OPEN_YOUTUBE


def test_youtube_search():
    assert detect_intent("pesquisar no youtube videos sobre python") == Intent.YOUTUBE_SEARCH


def test_screenshot():
    assert detect_intent("tirar um print da tela") == Intent.SCREENSHOT


def test_volume_up():
    assert detect_intent("aumentar o volume") == Intent.VOLUME_UP


def test_volume_down():
    assert detect_intent("diminuir o volume") == Intent.VOLUME_DOWN


@pytest.mark.parametrize("text", [
    "explique o que e inteligencia artificial",
    "o que e inteligencia artificial",
    "me explique inteligencia artificial",
    "poderia explicar inteligencia artificial",
])
def test_ask_ai_fallback(text):
    assert detect_intent(text) == Intent.ASK_AI


# --- parâmetros extraídos (seção 15 do pedido) -----------------------------

def test_calculate_params_extraction():
    match = classify("calcular 25 mais 50")
    assert match.intent == Intent.CALCULATE
    assert match.params["expression"] == "calcular 25 mais 50"


def test_weather_params_extraction():
    match = classify("previsao do tempo para sao paulo")
    assert match.intent == Intent.WEATHER
    assert match.params["city"] == "sao paulo"


def test_youtube_search_params_extraction():
    match = classify("pesquisar no youtube videos sobre python")
    assert match.intent == Intent.YOUTUBE_SEARCH
    assert match.params["query"] == "videos sobre python"


# --- diálogo de exemplo (seção 25 do pedido): deve executar direto, sem
# pedir confirmação, mesmo com o "Nero" e a pontuação da fala completa -----

@pytest.mark.parametrize("text,expected_intent", [
    ("Nero, você sabe me dizer qual é a data de hoje?", Intent.GET_DATE),
    ("Nero, e que horas são?", Intent.GET_TIME),
    ("Nero, quero colocar um compromisso na minha agenda.", Intent.ADD_AGENDA),
    ("Nero você pode me dizer que dia é hoje?", Intent.GET_DATE),
    ("Nero me fala a data.", Intent.GET_DATE),
])
def test_showcase_dialogue_executes_without_confirmation(text, expected_intent):
    match = _route(text)
    assert match.intent == expected_intent
    assert match.confidence >= CONFIDENCE_EXECUTE


# --- falsos positivos (seção 22 do pedido): tópico != comando --------------

def test_false_positive_story_about_a_day_is_not_get_date():
    assert detect_intent("conte uma historia sobre um dia na vida de um programador") != Intent.GET_DATE


def test_false_positive_explaining_agenda_is_not_read_agenda():
    assert detect_intent("explique como funciona uma agenda") != Intent.READ_AGENDA


def test_false_positive_talking_about_face_recognition_does_not_trigger_it():
    assert detect_intent("fale sobre reconhecimento facial") != Intent.FACE_RECOGNITION
