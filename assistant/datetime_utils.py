import random
from datetime import datetime

WEEKDAYS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]
MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

TIME_TEMPLATES = [
    "Agora são {h} horas e {m} minutos.",
    "São {h} horas e {m} minutos.",
    "Neste momento são {h} horas e {m} minutos.",
]
TIME_TEMPLATES_ON_HOUR = [
    "Agora são {h} horas em ponto.",
    "São {h} horas em ponto.",
]
DATE_TEMPLATES = [
    "Hoje é {weekday}, {day} de {month} de {year}.",
    "Hoje é dia {day} de {month}, {weekday}.",
]


def get_time_response() -> str:
    now = datetime.now()
    if now.minute == 0:
        return random.choice(TIME_TEMPLATES_ON_HOUR).format(h=now.hour)
    return random.choice(TIME_TEMPLATES).format(h=now.hour, m=now.minute)


def get_date_response() -> str:
    now = datetime.now()
    weekday = WEEKDAYS[now.weekday()]
    month = MONTHS[now.month - 1]
    return random.choice(DATE_TEMPLATES).format(weekday=weekday, day=now.day, month=month, year=now.year)
