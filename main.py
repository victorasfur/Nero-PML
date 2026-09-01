import argparse

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

from assistant.assistant import Assistant


def list_mics() -> None:
    import speech_recognition as sr

    names = sr.Microphone.list_microphone_names()
    if not names:
        print("Nenhum microfone foi detectado pelo Windows.")
        return
    print("Microfones detectados (use o índice com --mic-index):")
    for i, name in enumerate(names):
        print(f"  {i}: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nero - Assistente Virtual em Python")
    parser.add_argument(
        "--text-mode",
        action="store_true",
        help="Usa entrada de texto no terminal em vez do microfone "
        "(fallback para demonstração sem áudio/internet).",
    )
    parser.add_argument(
        "--mic-index",
        type=int,
        default=None,
        help="Força o uso de um microfone específico pelo índice "
        "(veja os índices disponíveis com --list-mics), caso o dispositivo "
        "padrão do Windows não seja o microfone correto.",
    )
    parser.add_argument(
        "--list-mics",
        action="store_true",
        help="Lista os microfones detectados pelo Windows e sai, sem iniciar a assistente.",
    )
    args = parser.parse_args()

    if args.list_mics:
        list_mics()
        return

    assistant = Assistant(text_mode=args.text_mode, mic_index=args.mic_index)
    assistant.run()


if __name__ == "__main__":
    main()
