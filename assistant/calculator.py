"""Calculadora por voz segura: NUNCA usa eval(). Parser dedicado que só aceita
os quatro operadores suportados, com números em dígitos ou por extenso (pt-BR)."""

import re
from typing import List, Optional, Tuple

NUMBER_WORDS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100, "cento": 100,
}

OPERATOR_ALIASES = {
    "mais": "add", "soma": "add", "somado": "add",
    "menos": "sub", "subtraido": "sub", "subtrai": "sub",
    "vezes": "mul", "multiplicado": "mul", "multiplicar": "mul",
    "dividido": "div", "dividir": "div",
}

_NUMERIC_RE = re.compile(r"-?\d+(\.\d+)?")


def _parse_trailing_number(tokens: List[str]) -> Optional[float]:
    """Lê o número mais próximo do FIM da lista (tolera texto solto antes)."""
    if not tokens:
        return None
    last = tokens[-1]
    if _NUMERIC_RE.fullmatch(last):
        return float(last)
    if len(tokens) >= 3 and tokens[-2] == "e":
        tens = NUMBER_WORDS.get(tokens[-3])
        units = NUMBER_WORDS.get(tokens[-1])
        if tens is not None and units is not None and tens >= 20 and units < 10:
            return float(tens + units)
    if last in NUMBER_WORDS:
        return float(NUMBER_WORDS[last])
    return None


def _parse_leading_number(tokens: List[str]) -> Optional[float]:
    """Lê o número mais próximo do INÍCIO da lista (tolera texto solto depois)."""
    if not tokens:
        return None
    first = tokens[0]
    if _NUMERIC_RE.fullmatch(first):
        return float(first)
    if len(tokens) >= 3 and tokens[1] == "e":
        tens = NUMBER_WORDS.get(tokens[0])
        units = NUMBER_WORDS.get(tokens[2])
        if tens is not None and units is not None and tens >= 20 and units < 10:
            return float(tens + units)
    if first in NUMBER_WORDS:
        return float(NUMBER_WORDS[first])
    return None


def calculate(expression: str) -> Tuple[Optional[float], Optional[str]]:
    """expression já deve estar normalizada (minúsculas, sem acento/pontuação).

    Retorna (resultado, None) em caso de sucesso, ou (None, codigo_do_erro):
    "invalid_expression" ou "division_by_zero".
    """
    tokens = expression.split()

    op_index = None
    op_code = None
    for i, tok in enumerate(tokens):
        if tok in OPERATOR_ALIASES:
            op_index = i
            op_code = OPERATOR_ALIASES[tok]
            break

    if op_index is None or op_index == 0 or op_index == len(tokens) - 1:
        return None, "invalid_expression"

    left_tokens = tokens[:op_index]
    right_tokens = tokens[op_index + 1:]
    # filler depois do operador: "multiplicado POR", "dividido POR",
    # "somado COM", "subtraido DE"
    if right_tokens and right_tokens[0] in ("por", "com", "de"):
        right_tokens = right_tokens[1:]

    num1 = _parse_trailing_number(left_tokens)
    num2 = _parse_leading_number(right_tokens)

    if num1 is None or num2 is None:
        return None, "invalid_expression"

    if op_code == "add":
        return num1 + num2, None
    if op_code == "sub":
        return num1 - num2, None
    if op_code == "mul":
        return num1 * num2, None
    if op_code == "div":
        if num2 == 0:
            return None, "division_by_zero"
        return num1 / num2, None

    return None, "invalid_expression"


def format_result(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".replace(".", ",")
