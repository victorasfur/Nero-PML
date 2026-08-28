from assistant.conversation_memory import ConversationMemory


def test_records_user_and_assistant_turns():
    mem = ConversationMemory(max_messages=20)
    mem.add_user("quem foi einstein")
    mem.add_assistant("um fisico alemao")
    history = mem.history()
    assert history == [
        {"role": "user", "content": "quem foi einstein"},
        {"role": "assistant", "content": "um fisico alemao"},
    ]


def test_blank_messages_are_ignored():
    mem = ConversationMemory()
    mem.add_user("   ")
    mem.add_assistant("")
    assert len(mem) == 0


def test_window_does_not_grow_past_limit():
    mem = ConversationMemory(max_messages=4)
    for i in range(10):
        mem.add_user(f"pergunta {i}")
        mem.add_assistant(f"resposta {i}")
    assert len(mem) == 4
    # mantém as MAIS RECENTES
    assert mem.history()[-1] == {"role": "assistant", "content": "resposta 9"}
    assert mem.history()[0] == {"role": "user", "content": "pergunta 8"}


def test_as_gemini_contents_maps_roles():
    mem = ConversationMemory()
    mem.add_user("oi")
    mem.add_assistant("ola")
    contents = mem.as_gemini_contents()
    assert contents == [
        {"role": "user", "parts": ["oi"]},
        {"role": "model", "parts": ["ola"]},
    ]


def test_clear():
    mem = ConversationMemory()
    mem.add_user("a")
    mem.clear()
    assert len(mem) == 0
