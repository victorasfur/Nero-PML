import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

print("\nVOZES DISPONÍVEIS:\n")

for i, voice in enumerate(voices):
    print(f"[{i}]")
    print(f"Nome: {voice.name}")
    print(f"ID: {voice.id}")
    print(f"Idioma: {getattr(voice, 'languages', [])}")
    print(f"Gênero: {getattr(voice, 'gender', 'não informado')}")
    print("-" * 50)