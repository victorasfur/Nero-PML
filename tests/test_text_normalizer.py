from assistant.text_normalizer import detect_wake_word, normalize_text


def test_normalize_lowercases_and_strips_accents():
    assert normalize_text("Nero, Que Horas São?") == "nero que horas sao"


def test_normalize_collapses_spaces():
    assert normalize_text("que    horas   sao") == "que horas sao"


def test_detect_wake_word_exact():
    found, count = detect_wake_word("nero que horas sao")
    assert found is True
    assert count == 1


def test_detect_wake_word_variant():
    found, _ = detect_wake_word("niro que horas sao")
    assert found is True


def test_detect_wake_word_absent():
    found, count = detect_wake_word("que horas sao")
    assert found is False
    assert count == 0


def test_detect_wake_word_not_false_positive_mid_sentence():
    found, _ = detect_wake_word("eu conheco um cara chamado nero")
    assert found is False
