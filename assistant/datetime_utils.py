from datetime import datetime

WEEKDAYS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]
MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def get_time_response() -> str:
    now = datetime.now()
    if now.minute == 0:
        return f"Agora são {now.hour} horas em ponto."
    return f"Agora são {now.hour} horas e {now.minute} minutos."


def get_date_response() -> str:
    now = datetime.now()
    weekday = WEEKDAYS[now.weekday()]
    month = MONTHS[now.month - 1]
    return f"Hoje é {weekday}, {now.day} de {month} de {now.year}."
