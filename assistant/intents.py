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
    SCREENSHOT = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    ASK_AI = auto()
