"""Utilitário de CADASTRO de faces (não é um comando de voz).

Uso:
    python -m vision.capture_faces "Nome Da Pessoa"

Abre a webcam, detecta o rosto e salva automaticamente N fotos em
vision/dataset/<Nome Da Pessoa>/. Pressione 'q' a qualquer momento para
interromper a captura.
"""

import sys

import cv2

from config import settings


def capture_faces(name: str, count: int = None) -> int:
    count = count or settings.FACE_CAPTURE_COUNT
    person_dir = settings.DATASET_DIR / name
    person_dir.mkdir(parents=True, exist_ok=True)

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
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
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                face_img = frame[y:y + h, x:x + w]
                img_path = person_dir / f"img_{saved + 1:02d}.jpg"
                cv2.imwrite(str(img_path), face_img)
                saved += 1
                break

            cv2.imshow("Cadastro de face - pressione q para sair", frame)
            if cv2.waitKey(200) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
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
