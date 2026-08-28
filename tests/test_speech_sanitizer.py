from assistant.speech_sanitizer import sanitize_for_speech


def test_strips_markdown_emphasis():
    assert sanitize_for_speech("Isso é **muito** importante e `código`") == "Isso é muito importante e código"


def test_pure_json_is_never_spoken():
    assert sanitize_for_speech('{"intent": "PLAY_MUSIC", "query": "Evidências"}') == "Certo."


def test_json_like_line_in_the_middle_is_cleaned_not_dropped():
    out = sanitize_for_speech("A resposta é [importante] e clara")
    assert "importante" in out and "[" not in out


def test_urls_become_the_word_link():
    assert sanitize_for_speech("veja em https://youtube.com/watch?v=abc agora") == "veja em link agora"


def test_markdown_link_keeps_only_the_text():
    assert sanitize_for_speech("clique em [YouTube](https://youtube.com)") == "clique em YouTube"


def test_list_markers_and_headers_removed():
    out = sanitize_for_speech("# Título\n- primeiro\n- segundo\n1. terceiro")
    assert out == "Título primeiro segundo terceiro"


def test_empty_stays_empty():
    assert sanitize_for_speech("") == ""
    assert sanitize_for_speech("   ") == ""
