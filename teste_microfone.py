import speech_recognition as sr

print("Microfones disponíveis:\n")

for i, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"[{i}] {name}")

print("\nDigite o índice do microfone que deseja testar.")
indice = int(input("Índice: "))

recognizer = sr.Recognizer()

with sr.Microphone(device_index=indice) as source:
    print("\nAjustando para o ruído ambiente...")
    recognizer.adjust_for_ambient_noise(source, duration=2)

    print("Fale alguma coisa...")
    audio = recognizer.listen(source, timeout=5)

print("\nÁudio capturado!")

try:
    texto = recognizer.recognize_google(audio, language="pt-BR")
    print(f"Você disse: {texto}")

except sr.UnknownValueError:
    print("Não consegui entender o que foi falado.")

except sr.RequestError as e:
    print(f"Erro no serviço de reconhecimento: {e}")