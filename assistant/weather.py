"""Previsão do tempo via Open-Meteo (gratuito, sem necessidade de API key)."""

import requests

from config import settings

WEATHER_CODES = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado", 3: "nublado",
    45: "névoa", 48: "névoa com geada",
    51: "garoa fraca", 53: "garoa moderada", 55: "garoa forte",
    61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte",
    71: "neve fraca", 73: "neve moderada", 75: "neve forte",
    80: "pancadas de chuva fracas", 81: "pancadas de chuva moderadas", 82: "pancadas de chuva fortes",
    95: "trovoadas",
}


def get_weather_response(city: str) -> str:
    city = (city or settings.DEFAULT_CITY).strip()
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "pt", "format": "json"},
            timeout=6,
        )
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return f"Não encontrei a cidade {city}."

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        resolved_name = results[0]["name"]

        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            },
            timeout=6,
        )
        forecast.raise_for_status()
        current = forecast.json().get("current", {})
        temp = current.get("temperature_2m")
        code = current.get("weather_code")

        if temp is None:
            return f"Não consegui obter a previsão do tempo para {resolved_name} agora."

        description = WEATHER_CODES.get(code, "condições variadas")
        return f"Em {resolved_name} agora está {description}, com {temp:.0f} graus."
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao consultar a previsão do tempo: {e}")
        return "Não consegui obter a previsão do tempo agora. Verifique sua conexão com a internet."
    except (KeyError, IndexError, ValueError) as e:
        print(f"[ERRO] Resposta inesperada da API de clima: {e}")
        return "Não consegui obter a previsão do tempo agora."
