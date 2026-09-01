"""Cotações de câmbio e bitcoin.

AwesomeAPI (economia.awesomeapi.com.br) era a única fonte, mas o tier
anônimo dela devolve 429 (Too Many Requests) de forma SUSTENTADA quando o
IP de saída é compartilhado (proxy corporativo, NAT) — não adianta tentar
de novo, o bloqueio não é uma rajada passageira. Por isso agora ela é só o
FALLBACK: a fonte primária de cada cotação é uma API sem chave e sem esse
histórico de limite agressivo; só cai para a AwesomeAPI se a primária
falhar.
"""

import time

import requests

# Fallback (AwesomeAPI): mantém um retry curto porque 5xx/timeout dela ainda
# costumam ser rajada passageira — só o 429 é que é persistente no cenário
# acima, mas não custa tentar mais uma vez.
_MAX_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 1.5


def _get_awesome_api(pair: str) -> dict:
    last_exc = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            resp = requests.get(f"https://economia.awesomeapi.com.br/json/last/{pair}", timeout=6)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            last_exc = e
            status = getattr(e.response, "status_code", None)
            retriable = status is None or status == 429 or status >= 500
            if attempt < _MAX_ATTEMPTS and retriable:
                time.sleep(_RETRY_DELAY_SECONDS * attempt)
                continue
            raise
    raise last_exc  # pragma: no cover - inatingível (o laço sempre retorna ou levanta antes)


def _get_dollar_rate() -> float:
    """USD -> BRL. Primária: open.er-api.com (gratuita, sem chave, sem
    histórico de limite agressivo). Cai para a AwesomeAPI se ela falhar."""
    try:
        resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=6)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") != "success":
            raise ValueError(f"resposta inesperada da open.er-api.com: {data}")
        return float(data["rates"]["BRL"])
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        print(f"[AVISO] open.er-api.com falhou ({e}); tentando AwesomeAPI...")
        data = _get_awesome_api("USD-BRL")
        return float(data["USDBRL"]["bid"])


def _get_bitcoin_rate() -> float:
    """BTC -> BRL. Primária: CoinGecko (gratuita, sem chave). Cai para a
    AwesomeAPI se ela falhar."""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "brl"},
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["bitcoin"]["brl"])
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        print(f"[AVISO] CoinGecko falhou ({e}); tentando AwesomeAPI...")
        data = _get_awesome_api("BTC-BRL")
        return float(data["BTCBRL"]["bid"])


def _format_brl(value: float) -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def _describe_request_error(e: requests.RequestException) -> str:
    status = getattr(e.response, "status_code", None)
    if status == 429:
        return "A consulta de câmbio está sendo muito usada agora. Tente de novo em alguns instantes."
    if status is not None:
        return "O serviço de câmbio está indisponível agora. Tente de novo mais tarde."
    return "Não consegui consultar a cotação agora. Verifique sua conexão com a internet."


def get_dollar_response() -> str:
    try:
        bid = _get_dollar_rate()
        return f"O dólar está cotado a {_format_brl(bid)} agora."
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao consultar o valor do dólar: {e}")
        return _describe_request_error(e)
    except (KeyError, ValueError, TypeError) as e:
        print(f"[ERRO] Resposta inesperada da API de câmbio: {e}")
        return "Não consegui consultar o valor do dólar agora."


def get_bitcoin_response() -> str:
    try:
        bid = _get_bitcoin_rate()
        return f"O bitcoin está cotado a {_format_brl(bid)} agora."
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao consultar o valor do bitcoin: {e}")
        return _describe_request_error(e)
    except (KeyError, ValueError, TypeError) as e:
        print(f"[ERRO] Resposta inesperada da API de câmbio: {e}")
        return "Não consegui consultar o valor do bitcoin agora."
