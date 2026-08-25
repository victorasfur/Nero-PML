from assistant import agenda


def test_creates_file_if_missing(tmp_path):
    agenda_file = tmp_path / "agenda.txt"
    assert not agenda_file.exists()
    agenda.ensure_agenda_file(agenda_file)
    assert agenda_file.exists()


def test_add_and_read_event(tmp_path):
    agenda_file = tmp_path / "agenda.txt"
    agenda.add_event("Reunião com o professor", agenda_file)
    assert agenda.read_events(agenda_file) == ["Reunião com o professor"]


def test_multiple_events(tmp_path):
    agenda_file = tmp_path / "agenda.txt"
    agenda.add_event("Evento 1", agenda_file)
    agenda.add_event("Evento 2", agenda_file)
    agenda.add_event("Evento 3", agenda_file)
    assert agenda.read_events(agenda_file) == ["Evento 1", "Evento 2", "Evento 3"]


def test_clear_agenda_keeps_file(tmp_path):
    agenda_file = tmp_path / "agenda.txt"
    agenda.add_event("Evento 1", agenda_file)
    agenda.clear_agenda(agenda_file)
    assert agenda_file.exists()
    assert agenda.read_events(agenda_file) == []


def test_read_creates_file_if_missing(tmp_path):
    agenda_file = tmp_path / "nova_agenda.txt"
    events = agenda.read_events(agenda_file)
    assert events == []
    assert agenda_file.exists()
