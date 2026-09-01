from enum import Enum, auto


class Intent(Enum):
    GET_DATE = auto()
    GET_TIME = auto()
    ADD_AGENDA = auto()
    READ_AGENDA = auto()
    CLEAR_AGENDA = auto()
    CALCULATE = auto()
    FACE_RECOGNITION = auto()
    REGISTER_FACE = auto()
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
    EASTER_EGG_CORINTHIANS = auto()
    EASTER_EGG_JOKE = auto()
    SHUTDOWN = auto()
    CHAT = auto()

    # Alias retrocompatível: o nome antigo era ASK_AI.
    ASK_AI = CHAT


# Intenções que a IA tem permissão de classificar. Ações destrutivas ou que
# mexem em dados do usuário (agenda) NÃO estão aqui de propósito: elas têm
# cobertura fuzzy boa e, no caso de limpar a agenda, um passo de confirmação
# falado próprio. A IA jamais decide sozinha executar algo fora desta lista.
# EASTER_EGG_CORINTHIANS e EASTER_EGG_JOKE também ficam de fora, mas por
# outro motivo: são gatilhos exatos ("vai/vamos Corinthians", "conte uma
# piada"), resolvidos só por regex — deixar a IA "decidir" quando disparar
# tiraria a graça de serem frases específicas.
# SHUTDOWN fica de fora pela mesma razão de segurança da agenda: encerrar o
# processo é uma ação de alto impacto (a sessão de conversa acaba) demais
# para depender de uma classificação da IA — só o gatilho exato por regex.
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
