import importlib.util
import os

speech_path = os.path.join("assistant", "speech.py")

spec = importlib.util.spec_from_file_location(
    "speech_test",
    speech_path
)

speech_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech_module)

SpeechEngine = speech_module.SpeechEngine

nero = SpeechEngine(text_mode=True)

nero.speak(
    "Olá. Eu sou Nero. Sistema inicializado com sucesso."
)
