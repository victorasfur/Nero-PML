import pytest

from assistant.parameter_extractors import extract_music_query, extract_youtube_query


@pytest.mark.parametrize("text,expected", [
    ("toque evidencias", "evidencias"),
    ("toca evidencias no youtube", "evidencias"),
    ("coloque uma musica do bruno mars", "do bruno mars"),
    ("quero ouvir musica sertaneja", "sertaneja"),
    ("coloque evidencias do chitaozinho e xororo", "evidencias do chitaozinho e xororo"),
    ("toca aquela musica que fala eu sei que vou te amar", "eu sei que vou te amar"),
    ("poe pra tocar musica do the beatles", "do the beatles"),
])
def test_extract_music_query(text, expected):
    assert extract_music_query(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("pesquisar no youtube videos sobre python", "python"),
    ("procure videos sobre python no youtube", "python"),
    ("quero videos de programacao python", "programacao python"),
    ("procure um video ensinando como fazer uma api em python", "como fazer uma api em python"),
    ("pesquise python no youtube", "python"),
    ("procura videos de receita de bolo", "receita de bolo"),
    ("me mostra videos de treino em casa", "treino em casa"),
])
def test_extract_youtube_query(text, expected):
    assert extract_youtube_query(text) == expected
