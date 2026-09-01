"""Utilitário de CADASTRO de faces (não é um comando de voz).

Uso:
    python -m vision.capture_faces "Nome Da Pessoa"

Abre a webcam, detecta o rosto e salva automaticamente N fotos em
vision/dataset/<Nome Da Pessoa>/. Pressione 'q' a qualquer momento para
interromper a captura.
"""

import os
import sys
import threading
import time

import cv2

from config import settings
from .camera import open_camera


def _sanitize_person_name(name: str) -> str:
    """Reduz `name` a um único componente de caminho seguro.

    `name` pode vir de fala transcrita ou de texto digitado pelo usuário
    (--text-mode) e é usado direto para montar um Path — sem isso, algo como
    "../../etc" viraria um diretório fora de vision/dataset/.
    """
    return os.path.basename((name or "").strip()).strip(". ")


def capture_faces(name: str, count: int = None) -> int:
    name = _sanitize_person_name(name)
    if not name:
        print("Nome inválido para cadastro de face.")
        return 0
    if name.lower() == "desconhecido":
        print('"desconhecido" é um nome reservado (ignorado pelo reconhecimento facial); escolha outro.')
        return 0

    count = count or settings.FACE_CAPTURE_COUNT
    person_dir = settings.DATASET_DIR / name
    person_dir.mkdir(parents=True, exist_ok=True)

    # cv2.imshow/waitKey/destroyAllWindows usam o backend nativo de janelas
    # (Cocoa no macOS) e só podem ser chamados na THREAD PRINCIPAL — no
    # app.py (GUI com pywebview), o Assistant roda numa thread de fundo, e
    # chamar essas funções lá derruba a thread com uma exceção nativa do
    # C++. CLI (main.py, python -m vision.capture_faces) roda na thread
    # principal e continua mostrando a prévia normalmente.
    show_preview = threading.current_thread() is threading.main_thread()

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = open_camera(0)
    if not cap.isOpened():
        print("Câmera não disponível.")
        return 0

    saved = 0
    print(f"Capturando {count} fotos de '{name}'. Olhe para a câmera. Pressione 'q' para cancelar.")
    try:
        while saved < count:
            ok, frame = cap.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            for (x, y, w, h) in detected:
                if show_preview:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                face_img = frame[y:y + h, x:x + w]
                img_path = person_dir / f"img_{saved + 1:02d}.jpg"
                cv2.imwrite(str(img_path), face_img)
                saved += 1
                break

            if show_preview:
                cv2.imshow("Cadastro de face - pressione q para sair", frame)
                if cv2.waitKey(200) & 0xFF == ord("q"):
                    break
            else:
                time.sleep(0.2)
    finally:
        cap.release()
        if show_preview:
            cv2.destroyAllWindows()

    print(f"{saved} foto(s) salva(s) em {person_dir}")
    return saved


if __name__ == "__main__":
    if len(sys.argv) > 1:
        person_name = sys.argv[1]
    else:
        person_name = input("Nome da pessoa a cadastrar: ").strip()

    if not person_name:
        print("Nome inválido.")
        sys.exit(1)

    capture_faces(person_name)
