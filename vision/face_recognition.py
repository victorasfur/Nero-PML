"""Reconhecimento facial com OpenCV: Haar Cascade (detecção) + LBPH (reconhecimento).

Escolhida por ser a opção com melhor relação instalação/estabilidade/documentação
para um projeto acadêmico no Windows: um único pacote (opencv-contrib-python),
sem compilação, 100% offline, e suficiente para um dataset pequeno em condições
controladas de demonstração.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from config import settings

FACE_SIZE = (200, 200)


def _get_cascade() -> cv2.CascadeClassifier:
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    return cv2.CascadeClassifier(cascade_path)


def _detect_largest_face(cascade: cv2.CascadeClassifier, gray_frame) -> Optional[Tuple[int, int, int, int]]:
    detected = cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5)
    if len(detected) == 0:
        return None
    return max(detected, key=lambda r: r[2] * r[3])


def _load_dataset(cascade: cv2.CascadeClassifier):
    """Treina o LBPH com as fotos em vision/dataset/<nome>/*.jpg.

    A pasta "desconhecido" é ignorada como rótulo — serve só de exemplo/documentação.
    Retorna (recognizer, label_map) ou (None, {}) se não houver ninguém cadastrado.
    """
    dataset_dir = settings.DATASET_DIR
    if not dataset_dir.exists():
        return None, {}

    faces = []
    labels = []
    label_map: Dict[int, str] = {}
    next_id = 0

    for person_dir in sorted(dataset_dir.iterdir()):
        if not person_dir.is_dir() or person_dir.name.lower() == "desconhecido":
            continue

        image_paths = [p for p in person_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        if not image_paths:
            continue

        label_map[next_id] = person_dir.name
        for img_path in image_paths:
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            box = _detect_largest_face(cascade, gray)
            if box is None:
                face = cv2.resize(gray, FACE_SIZE)
            else:
                x, y, w, h = box
                face = cv2.resize(gray[y:y + h, x:x + w], FACE_SIZE)
            faces.append(face)
            labels.append(next_id)
        next_id += 1

    if not faces:
        return None, {}

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    return recognizer, label_map


def recognize_face() -> str:
    cascade = _get_cascade()
    recognizer, label_map = _load_dataset(cascade)
    if recognizer is None:
        return "Nenhuma pessoa cadastrada no sistema de reconhecimento facial ainda."

    cap = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return "Câmera não disponível."

        for _ in range(30):
            ok, frame = cap.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            box = _detect_largest_face(cascade, gray)
            if box is None:
                continue

            x, y, w, h = box
            face = cv2.resize(gray[y:y + h, x:x + w], FACE_SIZE)
            label_id, confidence = recognizer.predict(face)

            if confidence <= settings.LBPH_CONFIDENCE_THRESHOLD:
                name = label_map.get(label_id, "Desconhecido")
                return f"{name}. Reconhecimento concluído."
            return "Desconhecido. Não reconheci essa pessoa."

        return "Não consegui identificar a pessoa."
    except cv2.error as e:
        print(f"[ERRO] Falha no OpenCV durante o reconhecimento facial: {e}")
        return "Ocorreu um erro ao tentar reconhecer a face."
    except Exception as e:
        print(f"[ERRO] Falha inesperada no reconhecimento facial: {e}")
        return "Ocorreu um erro ao tentar reconhecer a face."
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
