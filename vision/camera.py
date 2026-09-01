"""Abertura da webcam multiplataforma.

cv2.CAP_DSHOW é o backend DirectShow do Windows: acelera a abertura da
câmera nesse SO, mas não existe no macOS/Linux — passá-lo lá faz
cap.isOpened() sempre retornar False. Fora do Windows deixamos o OpenCV
escolher o backend padrão da plataforma (AVFoundation no macOS, V4L2 no
Linux).
"""

import sys

import cv2


def open_camera(index: int = 0) -> cv2.VideoCapture:
    if sys.platform.startswith("win"):
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)
    return cv2.VideoCapture(index)
