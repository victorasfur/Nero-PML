"""Diagnóstico standalone do microfone — não faz parte da aplicação, é só
para descobrir por que o áudio não está sendo capturado. Rode:

    python debug_mic.py

e fale alguma coisa quando ele disser "Pode falar...".
"""

import speech_recognition as sr

r = sr.Recognizer()

print("Dispositivos de entrada encontrados pelo SpeechRecognition:")
for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"  {i}: {name}")

mic = sr.Microphone()
print(f"\nUsando o microfone padrão do Windows (device_index=None).")

with mic as source:
    print("Calibrando ruído ambiente por 1s... fique em silêncio.")
    r.adjust_for_ambient_noise(source, duration=1)
    print(f"energy_threshold após calibração: {r.energy_threshold:.1f}")
    print("(Se esse número estiver muito alto, tipo > 3000-4000, o mic pode estar")
    print(" captando muito ruído de fundo ou o volume de entrada do Windows está alto demais.)")

    print("\nPode falar agora (você tem 6 segundos)...")
    try:
        audio = r.listen(source, timeout=6, phrase_time_limit=6)
    except sr.WaitTimeoutError:
        print("\nRESULTADO: TIMEOUT — nenhum som cruzou o limiar de energia.")
        print("Isso indica que o áudio NÃO está chegando ao programa: mic mudo,")
        print("volume de entrada em 0, dispositivo errado selecionado, ou driver.")
        raise SystemExit(0)

print("\nÁudio capturado! Tamanho:", len(audio.get_raw_data()), "bytes")
print("Enviando para o Google Speech Recognition (precisa de internet)...")

try:
    text = r.recognize_google(audio, language="pt-BR")
    print(f"\nRESULTADO: transcrito com sucesso -> \"{text}\"")
    print("O microfone e o reconhecimento de voz estão funcionando normalmente.")
except sr.UnknownValueError:
    print("\nRESULTADO: áudio foi CAPTURADO (mic funciona), mas o Google não")
    print("conseguiu entender a fala. Tente falar mais alto/claro e mais perto do mic.")
except sr.RequestError as e:
    print(f"\nRESULTADO: áudio foi CAPTURADO (mic funciona), mas falhou ao contatar")
    print(f"o serviço de reconhecimento (verifique sua internet): {e}")
