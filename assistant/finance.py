"""Cotações via AwesomeAPI (economia.awesomeapi.com.br) — gratuita, sem chave."""

import requests


def _get_awesome_api(pair: str) -> dict:
    resp = requests.get(f"https://economia.awesomeapi.com.br/json/last/{pair}", timeout=6)
    resp.raise_for_status()
    return resp.json()


def _format_brl(value: float) -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def get_dollar_response() -> str:
    try:
        data = _get_awesome_api("USD-BRL")
        bid = float(data["USDBRL"]["bid"])
        return f"O dólar está cotado a {_format_brl(bid)} agora."
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao consultar o valor do dólar: {e}")
        return "Não consegui consultar o valor do dólar agora. Verifique sua conexão com a internet."
    except (KeyError, ValueError) as e:
        print(f"[ERRO] Resposta inesperada da API de câmbio: {e}")
        return "Não consegui consultar o valor do dólar agora."


def get_bitcoin_response() -> str:
    try:
        data = _get_awesome_api("BTC-BRL")
        bid = float(data["BTCBRL"]["bid"])
        return f"O bitcoin está cotado a {_format_brl(bid)} agora."
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao consultar o valor do bitcoin: {e}")
        return "Não consegui consultar o valor do bitcoin agora. Verifique sua conexão com a internet."
    except (KeyError, ValueError) as e:
        print(f"[ERRO] Resposta inesperada da API de câmbio: {e}")
        return "Não consegui consultar o valor do bitcoin agora."
