from enum import Enum, auto


class Intent(Enum):
    GET_DATE = auto()
    GET_TIME = auto()
    ADD_AGENDA = auto()
    READ_AGENDA = auto()
    CLEAR_AGENDA = auto()
    CALCULATE = auto()
    FACE_RECOGNITION = auto()
    WEATHER = auto()
    DOLLAR = auto()
    BITCOIN = auto()
    OPEN_YOUTUBE = auto()
    YOUTUBE_SEARCH = auto()
    PLAY_MUSIC = auto()
    OPEN_BROWSER = auto()
    OPEN_GOOGLE = auto()
    OPEN_VSCODE = auto()
    SCREENSHOT = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    CHAT = auto()

    # Alias retrocompatível: o nome antigo era ASK_AI.
    ASK_AI = CHAT


# Intenções que a IA tem permissão de classificar. Ações destrutivas ou que
# mexem em dados do usuário (agenda) NÃO estão aqui de propósito: elas têm
# cobertura fuzzy boa e, no caso de limpar a agenda, um passo de confirmação
# falado próprio. A IA jamais decide sozinha executar algo fora desta lista.
AI_ALLOWED_INTENTS = {
    Intent.GET_DATE,
    Intent.GET_TIME,
    Intent.CALCULATE,
    Intent.WEATHER,
    Intent.DOLLAR,
    Intent.BITCOIN,
    Intent.OPEN_YOUTUBE,
    Intent.YOUTUBE_SEARCH,
    Intent.PLAY_MUSIC,
    Intent.OPEN_BROWSER,
    Intent.OPEN_GOOGLE,
    Intent.OPEN_VSCODE,
    Intent.SCREENSHOT,
    Intent.VOLUME_UP,
    Intent.VOLUME_DOWN,
    Intent.CHAT,
}
