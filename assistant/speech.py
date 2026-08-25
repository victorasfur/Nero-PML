import speech_recognition as sr
import pyttsx3

from config import settings


class InputClosed(Exception):
    """Sinaliza que a fonte de entrada acabou (EOF no --text-mode ou Ctrl+C)
    e o loop principal deve encerrar, em vez de continuar tentando ouvir."""


class SpeechEngine:
    """Encapsula reconhecimento de voz (STT) e síntese de voz (TTS).

    Em text_mode, listen() lê do teclado em vez do microfone — usado como
    fallback de demonstração caso o microfone/internet falhem ao vivo.
    """

    def __init__(self, text_mode: bool = False, mic_index: int = None):
        self.text_mode = text_mode
        self.mic_index = mic_index
        self.recognizer = None
        self.microphone = None
        self.tts_engine = None
        self._mic_available = False

        if not text_mode:
            self._init_microphone()
        self._init_tts()

    def _init_microphone(self) -> None:
        try:
            self.recognizer = sr.Recognizer()
            device_names = sr.Microphone.list_microphone_names()
            if not device_names:
                print(
                    "[AVISO] Nenhum microfone foi detectado pelo Windows. "
                    "Conecte um microfone ou defina um dispositivo de entrada padrão em "
                    "Configurações > Som. Rode com --text-mode enquanto isso."
                )
                self._mic_available = False
                return

            self.microphone = sr.Microphone(device_index=self.mic_index)
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                # Em alguns microfones (USB baratos, ruído de driver) a calibração acima
                # produz um limiar de energia absurdamente alto e a fala nunca é detectada.
                if self.recognizer.energy_threshold > settings.MIC_ENERGY_THRESHOLD_CEILING:
                    print(
                        f"[AVISO] Limiar de energia calibrado muito alto "
                        f"({self.recognizer.energy_threshold:.0f}); usando um valor mais "
                        f"sensível ({settings.MIC_ENERGY_THRESHOLD_FALLBACK}) para não perder fala."
                    )
                    self.recognizer.energy_threshold = settings.MIC_ENERGY_THRESHOLD_FALLBACK
                self.recognizer.dynamic_energy_threshold = True

            used_index = self.mic_index if self.mic_index is not None else "padrão do Windows"
            used_name = device_names[self.mic_index] if self.mic_index is not None else ""
            print(
                f"Microfone em uso: {used_name or '(dispositivo padrão)'} "
                f"[index={used_index}] | limiar de energia: {self.recognizer.energy_threshold:.0f}"
            )
            self._mic_available = True
        except Exception as e:
            # SpeechRecognition tem um bug conhecido: se Microphone.__enter__ falhar ao
            # abrir o stream, o __exit__ tenta fechar um stream inexistente e lança um
            # segundo erro (ex.: "'NoneType' object has no attribute 'close'") que mascara
            # a causa raiz real. Essa causa real fica em e.__context__ — exibimos as duas.
            root_cause = e.__context__ if e.__context__ is not None else e
            print(
                f"[AVISO] Microfone indisponível ({root_cause}). Provavelmente outro "
                "aplicativo está usando o microfone em modo exclusivo (Teams, Zoom, "
                "navegador, etc.) ou o dispositivo de entrada padrão do Windows mudou. "
                "Feche outros apps que usam o microfone e tente novamente, ou rode com --text-mode."
            )
            self._mic_available = False

    def _init_tts(self) -> None:
        try:
            self.tts_engine = pyttsx3.init()
            voices = self.tts_engine.getProperty("voices") or []
            chosen_id = None
            for voice in voices:
                blob = f"{voice.name} {voice.id} {getattr(voice, 'languages', [])}".lower()
                if "brazil" in blob or "portuguese" in blob or "pt-br" in blob or "pt_br" in blob:
                    chosen_id = voice.id
                    break
            if chosen_id:
                self.tts_engine.setProperty("voice", chosen_id)
            else:
                print(
                    "[AVISO] Nenhuma voz em português (Brasil) instalada no Windows foi encontrada. "
                    "Instale um pacote de voz pt-BR em Configurações > Hora e Idioma > Voz. "
                    "Usando a voz padrão do sistema por enquanto."
                )
            self.tts_engine.setProperty("rate", 175)
        except Exception as e:
            print(f"[AVISO] Não foi possível iniciar o sintetizador de voz (pyttsx3): {e}")
            self.tts_engine = None

    def speak(self, text: str) -> None:
        print(f"Nero: {text}")
        if not self.tts_engine:
            return
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"[AVISO] Falha ao sintetizar voz: {e}")

    def listen(self):
        """Retorna o texto transcrito, "" se ouviu algo mas não entendeu,
        ou None se não havia nada para capturar (silêncio/timeout/sem mic)."""
        if self.text_mode:
            try:
                text = input("Você (texto): ").strip()
            except EOFError:
                raise InputClosed("entrada de texto encerrada (EOF)")
            except KeyboardInterrupt:
                raise InputClosed("interrompido pelo usuário")
            return text or None

        if not self._mic_available:
            return None

        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=settings.LISTEN_TIMEOUT_SECONDS,
                    phrase_time_limit=settings.LISTEN_PHRASE_TIME_LIMIT,
                )
        except sr.WaitTimeoutError:
            return None
        except OSError as e:
            print(f"[ERRO] Problema ao acessar o microfone: {e}")
            return None

        try:
            return self.recognizer.recognize_google(audio, language="pt-BR")
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[ERRO] Falha ao contatar o serviço de reconhecimento de voz (verifique a internet): {e}")
            return None
