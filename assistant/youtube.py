import webbrowser
from urllib.parse import quote_plus


def open_youtube() -> None:
    webbrowser.open("https://www.youtube.com")


def search_youtube(query: str) -> None:
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query.strip())}")
