"""
app.py — ponte entre o Assistant real (assistant/assistant.py) e a
interface visual (nero.html), sem precisar alterar nenhum arquivo
dentro do pacote `assistant/`.

Coloque este arquivo na raiz do projeto, no mesmo nível de `main.py`
e de `nero.html`.

Como funciona:
  - Abre nero.html numa janela nativa com pywebview.
  - Assim que a janela carrega, cria o Assistant normalmente e
    "intercepta" (monkeypatch) alguns métodos/funções que ele já usa:
        speech.listen()      -> liga o estado "listening" e envia
                                 o texto transcrito pra tela
        speech.speak()       -> liga o estado "speaking" e mostra
                                 a resposta na tela
        commands.dispatch()  -> liga o estado "thinking" (é aqui que
        commands.execute()      entram as chamadas ao Gemini)
  - Depois disso chama assistant.run() normalmente — o loop de
    estados (WAITING_WAKE_WORD, WAITING_COMMAND, etc.) continua
    exatamente como você já implementou.

Instale a dependência que falta:
    pip install pywebview
"""

import json
import threading

# Precisa rodar ANTES de qualquer import que crie um contexto SSL (edge-tts,
# requests, speech_recognition etc.): faz a verificacao de certificado usar o
# repositorio de confianca do sistema operacional em vez do bundle do
# certifi, para funcionar em redes com inspecao de TLS (proxy corporativo,
# Zscaler etc.).
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    # truststore requer Python >= 3.10; em redes corporativas com inspecao de TLS,
    # instale: pip install truststore (requer upgrade para Python 3.10+)
    pass

import webview  # pip install pywebview

from assistant.assistant import Assistant
from assistant import commands as commands_module
from vision import capture_faces as capture_faces_module
from vision import face_recognition as face_recognition_module


# ---------------------------------------------------------------------------
# Funções de ponte — chamam JS na janela para atualizar a interface
# ---------------------------------------------------------------------------

def _js_string(texto: str) -> str:
    """Serializa um texto Python com segurança para uso dentro de evaluate_js."""
    return json.dumps(texto or "", ensure_ascii=False)


def ui_set_state(window: webview.Window, estado: str) -> None:
    # estado: 'idle' | 'listening' | 'thinking' | 'speaking'
    window.evaluate_js(f"Nero.setState({_js_string(estado)})")


def ui_set_transcript(window: webview.Window, texto: str) -> None:
    window.evaluate_js(f"Nero.setTranscript({_js_string(texto)})")


def ui_set_response(window: webview.Window, texto: str) -> None:
    window.evaluate_js(f"Nero.setResponse({_js_string(texto)})")


# ---------------------------------------------------------------------------
# Conecta a UI ao Assistant já existente, sem editar assistant/*.py
# ---------------------------------------------------------------------------

def conectar_ui(assistant: Assistant, window: webview.Window) -> None:
    # --- ouvir: self.speech.listen() -----------------------------------
    original_listen = assistant.speech.listen

    def listen_com_ui(*args, **kwargs):
        ui_set_state(window, "listening")
        texto = original_listen(*args, **kwargs)
        if texto:
            ui_set_transcript(window, texto)
        return texto

    assistant.speech.listen = listen_com_ui

    # --- falar: self.speech.speak() -------------------------------------
    original_speak = assistant.speech.speak

    def speak_com_ui(texto, *args, **kwargs):
        ui_set_state(window, "speaking")
        ui_set_response(window, texto)
        resultado = original_speak(texto, *args, **kwargs)
        ui_set_state(window, "idle")
        return resultado

    assistant.speech.speak = speak_com_ui

    # --- processar comando / chamada ao Gemini --------------------------
    # assistant.py faz "from . import commands" e chama commands.dispatch(...)
    # e commands.execute(...), então corrigir esses nomes no módulo já é
    # suficiente — não é preciso tocar em assistant.py.
    original_dispatch = commands_module.dispatch
    original_execute = commands_module.execute

    def dispatch_com_ui(*args, **kwargs):
        ui_set_state(window, "thinking")
        return original_dispatch(*args, **kwargs)

    def execute_com_ui(*args, **kwargs):
        ui_set_state(window, "thinking")
        return original_execute(*args, **kwargs)

    commands_module.dispatch = dispatch_com_ui
    commands_module.execute = execute_com_ui

    # --- câmera: vision.face_recognition.recognize_face() /
    # vision.capture_faces.capture_faces() ---------------------------------
    # Ambas fazem chamadas de câmera bloqueantes que podem levar alguns
    # segundos; ligamos o estado "camera" (indicador vermelho na UI) para
    # deixar claro que a webcam está ativa nesse intervalo, já que rodando
    # via GUI não há mais a prévia nativa do OpenCV (ver vision/camera.py e
    # o guard de thread principal em capture_faces.py / face_recognition.py).
    original_recognize_face = face_recognition_module.recognize_face

    def recognize_face_com_ui(*args, **kwargs):
        ui_set_state(window, "camera")
        resultado = original_recognize_face(*args, **kwargs)
        ui_set_state(window, "idle")
        return resultado

    face_recognition_module.recognize_face = recognize_face_com_ui

    original_capture_faces = capture_faces_module.capture_faces

    def capture_faces_com_ui(*args, **kwargs):
        ui_set_state(window, "camera")
        resultado = original_capture_faces(*args, **kwargs)
        ui_set_state(window, "idle")
        return resultado

    capture_faces_module.capture_faces = capture_faces_com_ui


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

def iniciar_backend(window: webview.Window) -> None:
    # Ajuste text_mode/mic_index aqui se precisar, igual você já faz
    # via argparse no main.py.
    assistant = Assistant(text_mode=False, mic_index=None)
    conectar_ui(assistant, window)
    ui_set_state(window, "idle")
    assistant.run()


def ao_carregar(window: webview.Window) -> None:
    thread = threading.Thread(target=iniciar_backend, args=(window,), daemon=True)
    thread.start()


def main() -> None:
    window = webview.create_window(
        title="Nero",
        url="nero.html",   # precisa estar na mesma pasta deste app.py
        width=900,
        height=700,
        background_color="#03060c",
    )
    window.events.loaded += lambda: ao_carregar(window)
    webview.start()  # bloqueia a thread principal até a janela fechar


if __name__ == "__main__":
    main()
